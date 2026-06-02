/*
 * Copyright (c) 2026
 * All rights reserved.
 */

#ifndef __ARCH_ARM_TLB_RESTORER_HH__
#define __ARCH_ARM_TLB_RESTORER_HH__

#include <string>

#include "arch/arm/tlb.hh"
#include "cpu/base.hh"
#include "params/ArmTLBRestorer.hh"
#include "sim/sim_object.hh"

namespace gem5
{

namespace ArmISA
{

class TLBRestorer : public SimObject
{
  public:
    TLBRestorer(const ArmTLBRestorerParams &p);

    void startup() override;

  private:
    BaseCPU *const cpu;
    TLB *const itb;
    TLB *const dtb;
    const int cpuId;
    const std::string checkpointFile;
};

} // namespace ArmISA
} // namespace gem5

#endif // __ARCH_ARM_TLB_RESTORER_HH__
