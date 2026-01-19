#!/usr/bin/env pwsh
<#
.SYNOPSIS
DDAS Backend Demo Test Runner - Quick Commands

.DESCRIPTION
Convenient PowerShell script to run various test configurations.

.EXAMPLE
.\test.ps1 all          # Run all tests
.\test.ps1 health       # Run health tests only
.\test.ps1 coverage     # Run with coverage report

#>

param(
    [Parameter(Position=0)]
    [string]$TestType = "all",
    
    [switch]$Verbose,
    [switch]$ShowPrint,
    [switch]$StopOnFail
)

# Set working directory
Set-Location "d:\DDAS\ddas\backend"

# Base pytest command
$baseCmd = @("pytest", "app/tests/test_demo.py")

# Build command based on test type
$cmd = $baseCmd.Clone()

switch ($TestType.ToLower()) {
    "all" {
        Write-Host "Running all demo tests..." -ForegroundColor Cyan
        $cmd += "-v"
    }
    
    "quick" {
        Write-Host "Running quick test suite..." -ForegroundColor Cyan
        $cmd += "-v", "-m", "health or auth"
    }
    
    "health" {
        Write-Host "Running health check tests..." -ForegroundColor Cyan
        $cmd += "-v", "-m", "health"
    }
    
    "auth" {
        Write-Host "Running authentication tests..." -ForegroundColor Cyan
        $cmd += "-v", "-m", "auth"
    }
    
    "fingerprint" {
        Write-Host "Running fingerprint ingestion tests..." -ForegroundColor Cyan
        $cmd += "-v", "-m", "fingerprint"
    }
    
    "detection" {
        Write-Host "Running detection engine tests..." -ForegroundColor Cyan
        $cmd += "-v", "-m", "detection"
    }
    
    "audit" {
        Write-Host "Running audit logging tests..." -ForegroundColor Cyan
        $cmd += "-v", "-m", "audit"
    }
    
    "integration" {
        Write-Host "Running integration tests..." -ForegroundColor Cyan
        $cmd += "-v", "-m", "integration"
    }
    
    "coverage" {
        Write-Host "Running tests with coverage report..." -ForegroundColor Cyan
        $cmd += "-v", "--cov=app", "--cov-report=term-missing"
    }
    
    "coverage-html" {
        Write-Host "Running tests with HTML coverage report..." -ForegroundColor Cyan
        $cmd += "-v", "--cov=app", "--cov-report=html"
    }
    
    "debug" {
        Write-Host "Running tests in debug mode..." -ForegroundColor Cyan
        $cmd += "-vvs", "--tb=long"
    }
    
    "single" {
        Write-Host "Running single test (provide test name)..." -ForegroundColor Cyan
        $testName = Read-Host "Enter test name (e.g., test_health_check)"
        $cmd += "-v", "-k", $testName
    }
    
    "help" {
        Write-Host @"
DDAS Backend Test Runner

Usage: .\test.ps1 [TestType] [Options]

Test Types:
  all              Run all demo tests
  quick            Run essential tests only
  health           Run health check tests
  auth             Run authentication tests
  fingerprint      Run fingerprint ingestion tests
  detection        Run detection engine tests
  audit            Run audit logging tests
  integration      Run integration tests
  coverage         Run with coverage report
  coverage-html    Generate HTML coverage report
  debug            Run in debug mode (verbose)
  single           Run a single test by name
  help             Show this help

Options:
  -Verbose         Show verbose output
  -ShowPrint       Show print statements
  -StopOnFail      Stop on first failure

Examples:
  .\test.ps1 all
  .\test.ps1 auth -Verbose
  .\test.ps1 coverage
  .\test.ps1 debug
  .\test.ps1 single

"@
        exit 0
    }
    
    default {
        Write-Host "Unknown test type: $TestType" -ForegroundColor Red
        Write-Host "Run: .\test.ps1 help" -ForegroundColor Yellow
        exit 1
    }
}

# Add optional flags
if ($Verbose) {
    $cmd += "-vv"
}
if ($ShowPrint) {
    $cmd += "-s"
}
if ($StopOnFail) {
    $cmd += "-x"
}

# Run tests
Write-Host ""
Write-Host "Command: $($cmd -join ' ')" -ForegroundColor Gray
Write-Host ""

& $cmd

# Check result
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ ALL TESTS PASSED - Backend is DEMO-READY" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "✗ Some tests failed - See output above" -ForegroundColor Red
    Write-Host ""
}

exit $LASTEXITCODE
