param (
    [switch]$Coverage,
    [string]$Path = "",
    [switch]$Verbose
)

$TestCommand = "pytest"

# Add coverage if specified
if ($Coverage) {
    $TestCommand += " --cov=app"
}

# Add specific path if provided
if ($Path -ne "") {
    $TestCommand += " $Path"
}

# Add verbose output if specified
if ($Verbose) {
    $TestCommand += " -v"
}

Write-Host "Running tests with command: $TestCommand" -ForegroundColor Green
Invoke-Expression $TestCommand
