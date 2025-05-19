# refactor_tests.ps1 - Helper script to assist with test refactoring

param(
    [string]$Action = "list"
)

# Directory containing tests
$testDir = ".\tests\test_api\test_routes\"

# List all files using authenticated_client
function List-FilesToRefactor {
    Write-Host "Files that need to be refactored to use auth_client_factory:" -ForegroundColor Yellow
    Write-Host "=======================================================" -ForegroundColor Yellow
    
    $files = Get-ChildItem -Path $testDir -Filter "*.py" | 
    Select-String -Pattern "authenticated_client" | 
    Select-Object Path -Unique
    
    foreach ($file in $files) {
        $filename = Split-Path $file.Path -Leaf
        $count = (Select-String -Path $file.Path -Pattern "authenticated_client").Count
        Write-Host "$filename - $count occurrences" -ForegroundColor Cyan
    }
    
    Write-Host "`nTotal files to refactor: $($files.Count)" -ForegroundColor Green
}

# Check progress of refactoring
function Check-RefactoringProgress {
    Write-Host "Checking refactoring progress..." -ForegroundColor Yellow
    
    $allFiles = Get-ChildItem -Path $testDir -Filter "*.py" | Measure-Object | Select-Object -ExpandProperty Count
    $filesToRefactor = (Get-ChildItem -Path $testDir -Filter "*.py" | 
        Select-String -Pattern "authenticated_client" | 
        Select-Object Path -Unique | 
        Measure-Object).Count
    
    $refactoredCount = $allFiles - $filesToRefactor
    $percentComplete = [math]::Round(($refactoredCount / $allFiles) * 100, 2)
    
    Write-Host "Progress: $refactoredCount / $allFiles files refactored ($percentComplete%)" -ForegroundColor Green
}

# Create a refactored version of a file (does not modify original)
function Create-RefactoredVersion {
    param(
        [string]$FileName
    )
    
    $fullPath = Join-Path $testDir $FileName
    $outputPath = $fullPath -replace '\.py$', '_refactored.py'
    
    if (-not (Test-Path $fullPath)) {
        Write-Host "Error: File $FileName not found" -ForegroundColor Red
        return
    }
    
    Write-Host "Creating refactored version of $FileName..." -ForegroundColor Yellow
    
    # Read the original file
    $content = Get-Content $fullPath -Raw
    
    # Apply basic replacements
    $content = $content -replace 'def test_(\w+)\(authenticated_client', 'def test_$1(auth_client_factory, test_user)'
    $content = $content -replace 'authenticated_client\.', 'client\.'
    
    # Add client creation statements
    $content = $content -replace '(def test_\w+\(auth_client_factory, test_user.*?\n\s*""".*?"""\n)', '$1    # Create a client with test user data\n    client = auth_client_factory()\n\n'
    
    # Output the refactored content
    Set-Content -Path $outputPath -Value $content
    
    Write-Host "Created refactored version at: $outputPath" -ForegroundColor Green
    Write-Host "Note: This is a basic transformation and will require manual review and editing." -ForegroundColor Yellow
}

# Run tests on both original and refactored versions
function Test-Refactored {
    param(
        [string]$FileName
    )
    
    $baseName = $FileName -replace '\.py$', ''
    $originalPath = Join-Path $testDir "$baseName.py"
    $refactoredPath = Join-Path $testDir "${baseName}_refactored.py"
    
    if (-not (Test-Path $originalPath)) {
        Write-Host "Error: Original file $originalPath not found" -ForegroundColor Red
        return
    }
    
    if (-not (Test-Path $refactoredPath)) {
        Write-Host "Error: Refactored file $refactoredPath not found" -ForegroundColor Red
        return
    }
    
    Write-Host "Testing original file: $baseName.py" -ForegroundColor Yellow
    python -m pytest $originalPath -v
    
    Write-Host "`nTesting refactored file: ${baseName}_refactored.py" -ForegroundColor Yellow
    python -m pytest $refactoredPath -v
}

# Main execution
switch ($Action) {
    "list" { List-FilesToRefactor }
    "progress" { Check-RefactoringProgress }
    "create" { 
        if ($args[0]) {
            Create-RefactoredVersion -FileName $args[0]
        }
        else {
            Write-Host "Error: Please provide a filename" -ForegroundColor Red
        }
    }
    "test" {
        if ($args[0]) {
            Test-Refactored -FileName $args[0]
        }
        else {
            Write-Host "Error: Please provide a filename" -ForegroundColor Red
        }
    }
    default {
        Write-Host "Unknown action. Valid actions are: list, progress, create <filename>, test <filename>" -ForegroundColor Red
    }
}
