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

#ifndef __ARCH_ARM_VA_TRANSLATOR_HH__
#define __ARCH_ARM_VA_TRANSLATOR_HH__

#include <string>
#include <vector>

#include "arch/arm/tlb.hh"
#include "cpu/base.hh"
#include "params/ArmVATranslator.hh"
#include "sim/sim_object.hh"

namespace gem5
{

namespace ArmISA
{

class VATranslator : public SimObject
{
  public:
    VATranslator(const ArmVATranslatorParams &p);

    void startup() override;

  private:
    struct VaEntry
    {
        Addr va;
        BaseMMU::Mode mode;
        uint64_t vpn;
        uint64_t ppn;
        bool has_misc_regs;
        uint64_t cpsr;
        uint64_t sctlr_el1;
        uint64_t tcr_el1;
        uint64_t ttbr0_el1;
        uint64_t ttbr1_el1;
        uint64_t mair_el1;
    };

    struct TranslationResult
    {
        VaEntry *va_entry;
        bool mismatch;
        bool valid;
        TlbEntry tlbEntry;
    };

    BaseCPU *const cpu;
    TLB *const itb;
    TLB *const dtb;
    const std::string vaFile;
    const std::string outDir;
    const int cpuId;
    const bool exitOnCompletion;
    std::vector<VaEntry> entries;

    void parseJSON();
    TranslationResult translateVA(const VaEntry *e, ThreadContext *tc);
    void writeResultsToCheckpoint(
        const std::vector<TranslationResult> &results) const;
    void injectRegs(ThreadContext *tc, const VaEntry &e) const;
};

} // namespace ArmISA
} // namespace gem5

#endif // __ARCH_ARM_VA_TRANSLATOR_HH__
