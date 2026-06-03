/*
 * Copyright (c) 2024 ARM Limited
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met: redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer;
 * redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution;
 * neither the name of the copyright holders nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include "arch/arm/va_translator.hh"

#include <sys/wait.h>
#include <unistd.h>

#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "nlohmann/json.hpp"

#include "arch/arm/pagetable.hh"
#include "arch/arm/regs/misc.hh"
#include "base/cprintf.hh"
#include "base/logging.hh"
#include "base/trace.hh"
#include "cpu/thread_context.hh"
#include "debug/VATranslator.hh"
#include "mem/request.hh"
#include "sim/serialize.hh"
#include "sim/sim_exit.hh"

namespace gem5
{

namespace ArmISA
{

VATranslator::VATranslator(const ArmVATranslatorParams &p)
    : SimObject(p),
      cpu(p.cpu),
      itb(p.itb),
      dtb(p.dtb),
      vaFile(p.va_file),
      outDir(p.out_dir),
      cpuId(p.cpu_id),
      exitOnCompletion(p.exit_on_completion)
{
}

namespace
{

std::string
readZstdFile(const std::string &path)
{
    int pipefd[2];
    if (pipe(pipefd) != 0) {
        fatal("ArmVATranslator: cannot create pipe for '%s'\n", path);
    }

    pid_t pid = fork();
    if (pid < 0) {
        close(pipefd[0]);
        close(pipefd[1]);
        fatal("ArmVATranslator: cannot fork for '%s'\n", path);
    }

    if (pid == 0) {
        close(pipefd[0]);
        if (dup2(pipefd[1], STDOUT_FILENO) < 0) {
            _exit(127);
        }
        close(pipefd[1]);
        execlp("zstd", "zstd", "-d", "-c", "--", path.c_str(),
               static_cast<char *>(nullptr));
        _exit(127);
    }

    close(pipefd[1]);
    std::string json;
    char buf[4096];
    ssize_t n = 0;
    while ((n = read(pipefd[0], buf, sizeof(buf))) > 0) {
        json.append(buf, n);
    }
    close(pipefd[0]);

    int status = 0;
    if (waitpid(pid, &status, 0) < 0) {
        fatal("ArmVATranslator: waitpid failed for '%s'\n", path);
    }
    if (n < 0) {
        fatal("ArmVATranslator: read failed while decompressing '%s'\n", path);
    }
    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
        fatal("ArmVATranslator: zstd failed for '%s' (status=%d)\n",
              path, status);
    }

    return json;
}

} // anonymous namespace

void
VATranslator::parseJSON()
{
    entries.clear();

    if (vaFile.empty()) {
        warn("ArmVATranslator: va_file is empty, nothing to translate.\n");
        return;
    }

    nlohmann::json root;
    if (vaFile.size() > 5 && vaFile.substr(vaFile.size() - 5) == ".zstd") {
        root = nlohmann::json::parse(readZstdFile(vaFile), nullptr, false);
    } else {
        std::ifstream f(vaFile);
        if (!f.is_open()) {
            fatal("ArmVATranslator: cannot open va_file '%s'\n", vaFile);
        }
        root = nlohmann::json::parse(f, nullptr, false);
    }
    if (root.is_discarded()) {
        fatal("ArmVATranslator: JSON parse error in '%s'\n", vaFile);
    }
    if (!root.is_array()) {
        fatal("ArmVATranslator: expected top-level JSON array in '%s'\n",
              vaFile);
    }

    const std::pair<const char *, BaseMMU::Mode> tlbKeys[] = {
        {"dtlb", BaseMMU::Read},
        {"itlb", BaseMMU::Execute},
    };

    if ((size_t)cpuId >= root.size()) {
        fatal("ArmVATranslator: cpuId=%d out of range (JSON has %lu CPUs)\n",
              cpuId, root.size());
    }

    const auto &cpu_json = root[cpuId];
    for (const auto &[tlbKey, mode] : tlbKeys) {
        if (!cpu_json.contains(tlbKey) ||
            !cpu_json[tlbKey].contains("entries")) {
            continue;
        }

        for (const auto &tlbSet : cpu_json[tlbKey]["entries"]) {
            if (!tlbSet.contains("entries")) {
                continue;
            }

            for (const auto &ent : tlbSet["entries"]) {
                try {
                    if (!ent.value("valid", false)) {
                        continue;
                    }

                    VaEntry e;
                    uint64_t vpn_json = ent.at("vpn").get<uint64_t>();
                    uint64_t ppn_json = ent.at("ppn").get<uint64_t>();
                    e.va = vpn_json << 12;
                    e.vpn = vpn_json;
                    e.ppn = ppn_json;
                    e.mode = mode;
                    const auto &asid_json = ent.at("asid");
                    if (asid_json.is_string()) {
                        e.global = true;
                        e.asid = 0;
                    } else {
                        e.global = false;
                        e.asid = static_cast<uint16_t>(
                            asid_json.at("NonGlobal").get<uint64_t>()
                        );
                    }
                    e.has_misc_regs = ent.contains("misc_regs");
                    if (e.has_misc_regs) {
                        const auto &mr = ent.at("misc_regs");
                        e.cpsr = mr.at("cpsr").get<uint64_t>();
                        e.sctlr_el1 = mr.at("sctlr_el1").get<uint64_t>();
                        e.tcr_el1 = mr.at("tcr_el1").get<uint64_t>();
                        e.ttbr0_el1 = mr.at("ttbr0_el1").get<uint64_t>();
                        e.ttbr1_el1 = mr.at("ttbr1_el1").get<uint64_t>();
                        e.mair_el1 = mr.at("mair_el1").get<uint64_t>();
                    } else {
                        e.cpsr = 0;
                        e.sctlr_el1 = 0;
                        e.tcr_el1 = 0;
                        e.ttbr0_el1 = 0;
                        e.ttbr1_el1 = 0;
                        e.mair_el1 = 0;
                    }
                    entries.push_back(e);
                } catch (const nlohmann::json::exception &ex) {
                    warn("ArmVATranslator: skipping TLB entry "
                         "(JSON error: %s)\n", ex.what());
                }
            }
        }
    }

    DPRINTF(VATranslator, "Parsed %lu entries from '%s' (CPU %d)\n",
            (unsigned long)entries.size(), vaFile, cpuId);
}

void
VATranslator::captureBaselineRegs(ThreadContext *tc)
{
    baselineRegs.cpsr = tc->readMiscRegNoEffect(MISCREG_CPSR);
    baselineRegs.sctlr_el1 = tc->readMiscRegNoEffect(MISCREG_SCTLR_EL1);
    baselineRegs.tcr_el1 = tc->readMiscRegNoEffect(MISCREG_TCR_EL1);
    baselineRegs.ttbr0_el1 = tc->readMiscRegNoEffect(MISCREG_TTBR0_EL1);
    baselineRegs.ttbr1_el1 = tc->readMiscRegNoEffect(MISCREG_TTBR1_EL1);
    baselineRegs.mair_el1 = tc->readMiscRegNoEffect(MISCREG_MAIR_EL1);
}

void
VATranslator::injectRegs(ThreadContext *tc, const VaEntry &e) const
{
    if (!e.has_misc_regs) {
        DPRINTF(VATranslator, "CPU %d: entry for VA=%#x has no misc_regs; "
                "using restored checkpoint EL1 state.\n", cpuId, e.va);
        tc->setMiscReg(MISCREG_CPSR, baselineRegs.cpsr);
        tc->setMiscReg(MISCREG_SCTLR_EL1, baselineRegs.sctlr_el1);
        tc->setMiscReg(MISCREG_TCR_EL1, baselineRegs.tcr_el1);
        tc->setMiscReg(MISCREG_TTBR0_EL1, baselineRegs.ttbr0_el1);
        tc->setMiscReg(MISCREG_TTBR1_EL1, baselineRegs.ttbr1_el1);
        tc->setMiscReg(MISCREG_MAIR_EL1, baselineRegs.mair_el1);
    } else {
        if (!(e.sctlr_el1 & 0x1)) {
            warn("ArmVATranslator: SCTLR_EL1.m=0 for VA=%#x -- MMU is off, "
                 "walk will be skipped (identity map).\n", e.va);
        }

        tc->setMiscReg(MISCREG_CPSR, e.cpsr);
        tc->setMiscReg(MISCREG_SCTLR_EL1, e.sctlr_el1);
        tc->setMiscReg(MISCREG_TCR_EL1, e.tcr_el1);
        tc->setMiscReg(MISCREG_TTBR0_EL1, e.ttbr0_el1);
        tc->setMiscReg(MISCREG_TTBR1_EL1, e.ttbr1_el1);
        tc->setMiscReg(MISCREG_MAIR_EL1, e.mair_el1);
    }
    tc->setMiscReg(MISCREG_HCR_EL2, 0);
    tc->setMiscReg(MISCREG_SCR_EL3, 0);
}

VATranslator::TranslationResult
VATranslator::translateVA(const VaEntry *e, ThreadContext *tc)
{
    TranslationResult result;
    result.va_entry = const_cast<VaEntry *>(e);
    result.mismatch = false;
    result.valid = false;

    BaseMMU::Mode mode = e->mode;
    TLB *tlb;
    const char *modeStr;
    switch (e->mode) {
      case BaseMMU::Read:
        tlb = dtb;
        modeStr = "Read";
        break;
      case BaseMMU::Write:
        tlb = dtb;
        modeStr = "Write";
        break;
      case BaseMMU::Execute:
        tlb = itb;
        modeStr = "Execute";
        break;
      default:
        warn("ArmVATranslator: VA=%#x unknown mode %d, skipping.\n",
             e->va, (int)e->mode);
        return result;
    }

    DPRINTF(VATranslator, "Translating VA=%#x mode=%s "
            "TTBR0=%#x TTBR1=%#x TCR=%#x MAIR=%#x ASID=%d\n",
            e->va, modeStr, e->ttbr0_el1, e->ttbr1_el1, e->tcr_el1,
            e->mair_el1,
            (int)((e->tcr_el1 & (1ULL << 22)) ?
                ((e->ttbr1_el1 >> 48) & 0xFF) :
                ((e->ttbr0_el1 >> 48) & 0xFF)));

    injectRegs(tc, *e);
    itb->updateMiscReg(tc, TLB::NormalTran);
    dtb->updateMiscReg(tc, TLB::NormalTran);
    itb->flushAll();
    dtb->flushAll();

    auto req = std::make_shared<Request>(
        e->va,
        4,
        0,
        Request::funcRequestorId,
        0,
        tc->contextId());

    TlbEntry *te = nullptr;
    Fault fault = tlb->getTE(
        &te,
        req,
        tc,
        mode,
        nullptr,
        false,
        true,
        false,
        TLB::NormalTran);

    if (fault == NoFault && te != nullptr) {
        result.valid = true;
        result.tlbEntry = *te;
        result.tlbEntry.asid = e->asid;
        result.tlbEntry.global = e->global;

        if (e->vpn != te->vpn || e->ppn != te->pfn) {
            result.mismatch = true;
            warn("ArmVATranslator: VPN/PPN mismatch for entry (CPU %d):\n"
                 "  Input VPN: 0x%lx, TLB VPN: 0x%lx\n"
                 "  Input PPN: 0x%lx, TLB PFN: 0x%lx\n",
                 cpuId, e->vpn, te->vpn, e->ppn, te->pfn);
        }
    } else {
        warn("ArmVATranslator: Translation FAULT for VA=%#x mode=%s "
             "(CPU %d, entry vpn=0x%lx)\n",
             e->va, modeStr, cpuId, e->vpn);
    }

    return result;
}

void
VATranslator::writeResultsToCheckpoint(
    const std::vector<TranslationResult> &results) const
{
    if (outDir.empty()) {
        DPRINTF(VATranslator, "CPU %d: output directory not specified, "
                "skipping checkpoint write.\n", cpuId);
        return;
    }

    std::string outFile = outDir + "/mmu-cpu" + std::to_string(cpuId) + ".cpt";
    std::ofstream outStream(outFile);
    if (!outStream.good()) {
        fatal("ArmVATranslator (CPU %d): cannot open checkpoint file '%s'\n",
              cpuId, outFile);
    }

    CheckpointOut &cp = outStream;

    std::string base = csprintf("system.cpu_cluster.cpus%d.mmu", cpuId);

    std::vector<const TranslationResult *> itbResults, dtbResults;
    for (const auto &res : results) {
        if (res.va_entry->mode == BaseMMU::Execute) {
            itbResults.push_back(&res);
        } else {
            dtbResults.push_back(&res);
        }
    }

    std::string itbpath = base + ".itb";
    cp << "\n[" << itbpath << "]\n";
    cp << "size=" << itbResults.size() << "\n";
    for (int i = 0; i < (int)itbResults.size(); i++) {
        cp << "\n[" << csprintf("%s.Entry%d", itbpath.c_str(), i) << "]\n";
        itbResults[i]->tlbEntry.serialize(cp);
    }

    std::string dtbpath = base + ".dtb";
    cp << "\n[" << dtbpath << "]\n";
    cp << "size=" << dtbResults.size() << "\n";
    for (int i = 0; i < (int)dtbResults.size(); i++) {
        cp << "\n[" << csprintf("%s.Entry%d", dtbpath.c_str(), i) << "]\n";
        dtbResults[i]->tlbEntry.serialize(cp);
    }

    DPRINTF(VATranslator, "CPU %d: wrote %d ITB + %d DTB entries to '%s'\n",
            cpuId, (int)itbResults.size(), (int)dtbResults.size(), outFile);
}

void
VATranslator::startup()
{
    DPRINTF(VATranslator, "Startup -- beginning VA translations\n");

    ThreadContext *tc = cpu->getContext(0);
    captureBaselineRegs(tc);

    parseJSON();

    std::vector<TranslationResult> results;
    for (const VaEntry &e : entries) {
        TranslationResult res = translateVA(&e, tc);
        if (res.valid) {
            results.push_back(res);
        }
    }

    writeResultsToCheckpoint(results);

    itb->flushAll();
    dtb->flushAll();
    itb->drainResume();
    dtb->drainResume();

    DPRINTF(VATranslator, "CPU %d: done -- %lu VAs translated\n",
            cpuId, (unsigned long)entries.size());

    if (exitOnCompletion) {
        exitSimLoop("ArmVATranslator done", 0, curTick());
    }
}

} // namespace ArmISA
} // namespace gem5
