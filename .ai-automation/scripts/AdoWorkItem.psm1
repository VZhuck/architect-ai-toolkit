class AdoWorkItem {
    [string]$Id
    [string]$Title
    [string]$Description
    [string]$AcceptanceCriteria

    AdoWorkItem([object]$cap) {
        $this.Id = [string]$cap.id
        $this.Title = [string]$cap.fields.'System.Title'
        $this.Description = [string]$cap.fields.'System.Description'
        $this.AcceptanceCriteria = [string]$cap.fields.'Microsoft.VSTS.Common.AcceptanceCriteria'
    }
}