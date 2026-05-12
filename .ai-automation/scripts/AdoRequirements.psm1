using module .\AdoWorkItem.psm1

class AdoRequirements {
    [AdoWorkItem]$Capability
    [AdoWorkItem[]]$Features

    AdoRequirements([AdoWorkItem]$capability, [AdoWorkItem[]]$features) {
        $this.Capability = $capability
        $this.Features = $features
    }
}