/*
 * Copyright (c) 2026
 * All rights reserved.
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
    } catch (...) {
        fs::remove_all(temp_dir);
        throw;
    }

    fs::remove_all(temp_dir);
}

} // namespace ArmISA
} // namespace gem5
