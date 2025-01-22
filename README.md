## HomeAssistant HACS Integration for Fenecon Fems Systems


# Fenecon Fems Integration

## Overview

This is a custom integration for HomeAssistant HACS that allows you to monitor and control your Fenecon Fems systems. The integration requires the IP address, username, and password of your Fenecon Fems device.

## Installation

1. Ensure you have [HACS](https://hacs.xyz/) installed in your HomeAssistant setup.
2. Add this repository to HACS as a custom repository.
3. Search for "Fenecon Fems Integration" in HACS and install it.

## Configuration

1. Go to the HomeAssistant Configuration page.
2. Click on "Integrations".
3. Click on the "+ Add Integration" button.
4. Search for "Fenecon Fems Integration".
5. Enter the IP address, username, and password of your Fenecon Fems device.
6. By default the username is ```x``` and the password is ```user```

## Usage

Once configured, the integration will create sensors for various data points provided by your Fenecon Fems system. These sensors can be used in your HomeAssistant dashboards, automations, and scripts.

## Data Points

The integration provides the following data points:
- State
- EssSoc
- EssActivePower
- EssReactivePower
- GridActivePower
- GridMinActivePower
- GridMaxActivePower
- ProductionActivePower
- ProductionMaxActivePower
- ProductionAcActivePower
- ProductionDcActualPower
- ConsumptionActivePower
- ConsumptionMaxActivePower
- EssActiveChargeEnergy
- EssActiveDischargeEnergy
- GridBuyActiveEnergy
- GridSellActiveEnergy
- ProductionActiveEnergy
- ProductionAcActiveEnergy
- ProductionDcActiveEnergy
- ConsumptionActiveEnergy
- EssDcChargeEnergy
- EssDcDischargeEnergy
- EssDischargePower
- GridMode

## Troubleshooting

If you encounter any issues, please check the HomeAssistant logs for error messages. Ensure that the IP address, username, and password are correct and that your Fenecon Fems device is reachable from your HomeAssistant instance.

## Fenecon Fems Api

The integration uses the Fenecon Fems API to retrieve data from your Fenecon Fems system. The API documentation can be found [here](https://docs.fenecon.de/de/fems/fems-app/App_REST-JSON_Lesezugriff.html).
