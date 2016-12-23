/*
 * Simple shell application for the ethernet proxy.
 *
 * This initializes the ethernet hardware, and enables DMA.
 * From then on, the debugger is expected to communicate
 * directly with the hardware via shared SRAM.
 *
 * No link detection or auto-negotiation, on purpose.
 * Hardcoded to 10baseT full duplex mode.
 */

#include <stdbool.h>
#include <stdint.h>
#include "inc/hw_memmap.h"
#include "inc/hw_emac.h"
#include "driverlib/gpio.h"
#include "driverlib/emac.h"
#include "driverlib/rom_map.h"
#include "driverlib/sysctl.h"
#include "drivers/pinout.h"

void capture_phy_regs(void);
void init_dma_frames(void);

typedef struct {
    tEMACDMADescriptor desc;
    uint8_t frame[1536];
} tDMAFrame;

uint32_t g_ui32SysClock;

struct {
    uint32_t bmcr, bmsr, cfg1, sts;
} g_phy;

tDMAFrame g_rxBuffer[8];
tDMAFrame g_txBuffer[8];

int main(void)
{
    MAP_SysCtlMOSCConfigSet(SYSCTL_MOSC_HIGHFREQ);
    g_ui32SysClock = MAP_SysCtlClockFreqSet((SYSCTL_XTAL_25MHZ |
                                             SYSCTL_OSC_MAIN |
                                             SYSCTL_USE_PLL |
                                             SYSCTL_CFG_VCO_480), 120000000);

    PinoutSet(true, false);

    MAP_SysCtlPeripheralEnable(SYSCTL_PERIPH_EMAC0);
    MAP_SysCtlPeripheralReset(SYSCTL_PERIPH_EMAC0);
    MAP_SysCtlPeripheralEnable(SYSCTL_PERIPH_EPHY0);
    MAP_SysCtlPeripheralReset(SYSCTL_PERIPH_EPHY0);
    while (!MAP_SysCtlPeripheralReady(SYSCTL_PERIPH_EMAC0));

    MAP_EMACPHYConfigSet(EMAC0_BASE,  
                         EMAC_PHY_TYPE_INTERNAL |
                         EMAC_PHY_INT_MDI_SWAP |
                         EMAC_PHY_INT_FAST_L_UP_DETECT |
                         EMAC_PHY_INT_EXT_FULL_DUPLEX |
                         EMAC_PHY_FORCE_10B_T_FULL_DUPLEX);

    MAP_EMACReset(EMAC0_BASE);

    MAP_EMACInit(EMAC0_BASE, g_ui32SysClock,
                 EMAC_BCONFIG_MIXED_BURST | EMAC_BCONFIG_PRIORITY_FIXED,
                 8, 8, 0);

    MAP_EMACConfigSet(EMAC0_BASE,
                      (EMAC_CONFIG_FULL_DUPLEX |
                       EMAC_CONFIG_7BYTE_PREAMBLE |
                       EMAC_CONFIG_IF_GAP_96BITS |
                       EMAC_CONFIG_USE_MACADDR0 |
                       EMAC_CONFIG_SA_FROM_DESCRIPTOR |
                       EMAC_CONFIG_BO_LIMIT_1024),
                      (EMAC_MODE_RX_STORE_FORWARD |
                       EMAC_MODE_TX_STORE_FORWARD ), 0);

    MAP_EMACFrameFilterSet(EMAC0_BASE, EMAC_FRMFILTER_RX_ALL);

    init_dma_frames();

    MAP_EMACTxEnable(EMAC0_BASE);
    MAP_EMACRxEnable(EMAC0_BASE);

    while (1) {
        capture_phy_regs();
        __asm__ volatile ("bkpt");
    }
}

void init_dma_frames(void)
{
    const uint32_t num_tx = sizeof(g_txBuffer) / sizeof(g_txBuffer[0]);
    const uint32_t num_rx = sizeof(g_rxBuffer) / sizeof(g_rxBuffer[0]);
    uint32_t i;

    for (i = 0; i < num_tx; i++) {
        g_txBuffer[i].desc.ui32Count = (sizeof g_txBuffer[0].frame << DES1_TX_CTRL_BUFF1_SIZE_S);
        g_txBuffer[i].desc.pvBuffer1 = g_txBuffer[i].frame;
        g_txBuffer[i].desc.DES3.pLink = &g_txBuffer[(i + 1) % num_tx].desc;
        g_txBuffer[i].desc.ui32CtrlStatus = 0;
    }

    for (i = 0; i < num_rx; i++) {
        g_rxBuffer[i].desc.ui32Count = DES1_RX_CTRL_CHAINED | (sizeof g_rxBuffer[0].frame << DES1_RX_CTRL_BUFF1_SIZE_S);
        g_rxBuffer[i].desc.pvBuffer1 = g_rxBuffer[i].frame;
        g_rxBuffer[i].desc.DES3.pLink = &g_rxBuffer[(i + 1) % num_rx].desc;
        g_rxBuffer[i].desc.ui32CtrlStatus = DES0_RX_CTRL_OWN;
    }

    MAP_EMACRxDMADescriptorListSet(EMAC0_BASE, &g_rxBuffer[0].desc);
    MAP_EMACTxDMADescriptorListSet(EMAC0_BASE, &g_txBuffer[0].desc);
}

void capture_phy_regs(void)
{
    // It's inconvenient to read PHY registers from the debugger.
    // Help out by copying the ones we're interested in to RAM.

    g_phy.bmcr = MAP_EMACPHYRead(EMAC0_BASE, 0, EPHY_BMCR);
    g_phy.bmsr = MAP_EMACPHYRead(EMAC0_BASE, 0, EPHY_BMSR);
    g_phy.cfg1 = MAP_EMACPHYRead(EMAC0_BASE, 0, EPHY_CFG1);
    g_phy.sts = MAP_EMACPHYRead(EMAC0_BASE, 0, EPHY_STS);
}