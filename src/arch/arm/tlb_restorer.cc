/*
 * Copyright (c) 2026 ARM Limited
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

#include "arch/arm/tlb_restorer.hh"

#include <filesystem>

#include "base/cprintf.hh"
#include "base/logging.hh"
#include "debug/Checkpoint.hh"
#include "sim/serialize.hh"

namespace fs = std::filesystem;

namespace gem5
{

namespace ArmISA
{

TLBRestorer::TLBRestorer(const ArmTLBRestorerParams &p)
    : SimObject(p),
      cpu(p.cpu),
      itb(p.itb),
      dtb(p.dtb),
      cpuId(p.cpu_id),
      checkpointFile(p.checkpoint_file)
{
}

void
TLBRestorer::startup()
{
    if (checkpointFile.empty()) {
        warn("ArmTLBRestorer: checkpoint_file is empty, skipping.\n");
        return;
    }

    fs::path sidecar(checkpointFile);
    if (!fs::is_regular_file(sidecar)) {
        warn("ArmTLBRestorer: checkpoint file not found: %s\n",
             checkpointFile.c_str());
        return;
    }

    fs::path temp_dir = fs::temp_directory_path() /
        csprintf("gem5-tlb-restore-%d-%s", cpuId, name().c_str());
    fs::remove_all(temp_dir);
    fs::create_directories(temp_dir);

    try {
        fs::copy_file(
            sidecar,
            temp_dir / CheckpointIn::baseFilename,
            fs::copy_options::overwrite_existing
        );

        CheckpointIn cp(temp_dir.string());
        itb->flushAll();
        dtb->flushAll();
        itb->unserializeSection(
            cp, csprintf("system.cpu_cluster.cpus%d.mmu.itb", cpuId)
        );
        dtb->unserializeSection(
            cp, csprintf("system.cpu_cluster.cpus%d.mmu.dtb", cpuId)
        );
        itb->drainResume();
        dtb->drainResume();
    } catch (...) {
        fs::remove_all(temp_dir);
        throw;
    }

    fs::remove_all(temp_dir);
}

} // namespace ArmISA
} // namespace gem5
