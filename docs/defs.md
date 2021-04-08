# JESD204 Definitions

To better understand the system as a whole common definitions must be used between converters, clock chips, and FPGAs used within the system. This page will outline the different clocks and standard configuration parameters for JESD204B and JESD204C.

### Link parameters

<!-- vale off -->

**E**
: Number of multiblocks in an extended multiblock

**F**
: Octets per frame per link

**HD**
: High Density User Data Format

**K**
: Frames per multiframe

**L**
: Number of lanes

**M**
: Number of virtual converters

**N**
: Number of non-dummy bits per sample. Usually converter resolution.

**Np**
: Number of bits per sample

**S**
: Samples per converter per frame

<!-- vale on -->

### Clocks

<!-- vale off -->
**frame_clock**
: Frames per second $$ \text{frame clock} = \frac{\text{sample clock}}{S} $$. Clock rate at which samples are generated/processed. Has the same rate as the conversion clock, except for interpolating DACs or decimating DACs, where it is slower by the interpolation/decimation factor.
<!-- vale on -->

**sample clock**
: Data rate in samples per second after decimation stages for ADCs or before interpolation stages for DACs. This is usually referred to as device clock

**local multi-frame clock (LMFC)**
: Clock which is equivalent to the link clock counts $$ LMFC = (F \times K/4) $$

**system reference (SYSREF) clock**
: Clock used for synchronization in subclass 1 and subclass 2 configurations for deterministic latency. It is assumed to be aligned with the sample clock from the clock chip but with periods at integer multiples of the device clock.

**character clock**
: Clock with which 8b10b characters and octets are generated.

**conversion clock**
: Clock used by a converter device to perform the A2D or D2A conversion.

**device clock**
: Master clock supplied to the JESD204B device from which all other clock signals must be derived.

**line clock**
: Clock for the high-speed serial interface.

**local clock**
: A clock generated inside a JESD204B device.

**SYSREF clock**
: Slow clock used for cross-device synchronization purposes.

!!! info "All clocks inside a JESD204B system must have a integer relationship"

### Control characters

**/R/ K28.0**
: Initial lane alignment sequence multi-frame start.

**/A/ K28.3**
: Lane alignment

**/Q/ K28.4**
: Initial lane alignment sequence configuration marker.

**/K/ K28.5**
: Code group synchronization.

**/F/ K28.7**
: Frame synchronization.

### Abbreviations

**CGS**
: Code Group Synchronization

**ILAS**
: Initial Lane Alignment Sequence

**LMFC**
: Local Multi Frame Clock

**LEMC**
: Local Extended Multiblock Clock

**MCDA**
: Multiple Converter Device Alignment

**NMCDA**
: No Multiple Converter Device Alignment

**RBD**
: RX Buffer Delay

**EMB**
: Extended Multiblock

**EoMB**
: End-of-multiblock sequence (00001)

**EoEMB**
: End of extended multiblock identifier bit
