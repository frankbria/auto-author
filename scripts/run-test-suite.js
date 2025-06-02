#!/usr/bin/env node

/**
 * Comprehensive Test Suite Runner
 * Validates and runs all test infrastructure components
 */

const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.join(__dirname, '..');
const FRONTEND_DIR = path.join(ROOT_DIR, 'frontend');
const BACKEND_DIR = path.join(ROOT_DIR, 'backend');

class TestSuiteRunner {
  constructor() {
    this.results = {
      frontend: { unit: null, e2e: null, integration: null },
      backend: { unit: null, integration: null, load: null, performance: null },
      overall: { passed: 0, failed: 0, skipped: 0 }
    };
  }

  log(level, message) {
    const timestamp = new Date().toISOString();
    const colors = {
      'INFO': '\x1b[36m',
      'SUCCESS': '\x1b[32m',
      'WARNING': '\x1b[33m',
      'ERROR': '\x1b[31m'
    };
    const reset = '\x1b[0m';
    console.log(`${colors[level]}[${timestamp}] ${level}: ${message}${reset}`);
  }

  async execCommand(command, options = {}) {
    return new Promise((resolve, reject) => {
      this.log('INFO', `Executing: ${command}`);
      
      const child = spawn(command, [], {
        shell: true,
        stdio: 'inherit',
        ...options
      });

      child.on('close', (code) => {
        if (code === 0) {
          resolve({ success: true, code });
        } else {
          resolve({ success: false, code });
        }
      });

      child.on('error', (error) => {
        reject(error);
      });
    });
  }

  async runFrontendTests() {
    this.log('INFO', '=== Running Frontend Tests ===');
    
    try {
      // Change to frontend directory
      process.chdir(FRONTEND_DIR);
      
      // Check if dependencies are installed
      if (!fs.existsSync(path.join(FRONTEND_DIR, 'node_modules'))) {
        this.log('WARNING', 'node_modules not found. Installing dependencies...');
        const installResult = await this.execCommand('npm install');
        if (!installResult.success) {
          throw new Error('Failed to install frontend dependencies');
        }
      }

      // Run unit tests
      this.log('INFO', 'Running frontend unit tests...');
      const unitResult = await this.execCommand('npm test -- --passWithNoTests --verbose');
      this.results.frontend.unit = unitResult.success;

      // Run integration tests
      this.log('INFO', 'Running frontend integration tests...');
      const integrationResult = await this.execCommand('npm test -- --testNamePattern="Integration" --passWithNoTests');
      this.results.frontend.integration = integrationResult.success;

      // Install Playwright if needed and run E2E tests
      this.log('INFO', 'Checking Playwright installation...');
      try {
        await this.execCommand('npx playwright install --with-deps');
        this.log('INFO', 'Running E2E tests...');
        const e2eResult = await this.execCommand('npm run test:e2e');
        this.results.frontend.e2e = e2eResult.success;
      } catch (error) {
        this.log('WARNING', `E2E tests skipped: ${error.message}`);
        this.results.frontend.e2e = null;
      }

    } catch (error) {
      this.log('ERROR', `Frontend tests failed: ${error.message}`);
      this.results.frontend.unit = false;
      this.results.frontend.integration = false;
      this.results.frontend.e2e = false;
    } finally {
      process.chdir(ROOT_DIR);
    }
  }

  async runBackendTests() {
    this.log('INFO', '=== Running Backend Tests ===');
    
    try {
      // Change to backend directory
      process.chdir(BACKEND_DIR);
      
      // Check if virtual environment should be used
      const hasVenv = fs.existsSync(path.join(BACKEND_DIR, 'venv')) || 
                     fs.existsSync(path.join(BACKEND_DIR, '.venv'));
      
      const pythonCmd = hasVenv ? 
        (process.platform === 'win32' ? '.venv\\Scripts\\python' : './venv/bin/python') : 
        'python';
      
      const pipCmd = hasVenv ? 
        (process.platform === 'win32' ? '.venv\\Scripts\\pip' : './venv/bin/pip') : 
        'pip';

      // Install dependencies if requirements.txt exists
      if (fs.existsSync(path.join(BACKEND_DIR, 'requirements.txt'))) {
        this.log('INFO', 'Installing backend dependencies...');
        try {
          await this.execCommand(`${pipCmd} install -r requirements.txt`);
        } catch (error) {
          this.log('WARNING', `Failed to install requirements: ${error.message}`);
        }
      }

      // Run unit tests
      this.log('INFO', 'Running backend unit tests...');
      const unitResult = await this.execCommand(`${pythonCmd} -m pytest tests/ -v --tb=short -x`);
      this.results.backend.unit = unitResult.success;

      // Run integration tests
      this.log('INFO', 'Running backend integration tests...');
      const integrationResult = await this.execCommand(`${pythonCmd} -m pytest tests/integration/ -v --tb=short`);
      this.results.backend.integration = integrationResult.success;

      // Run performance tests (if applicable)
      if (fs.existsSync(path.join(BACKEND_DIR, 'tests', 'performance'))) {
        this.log('INFO', 'Running performance tests...');
        const perfResult = await this.execCommand(`${pythonCmd} tests/performance/benchmark.py`);
        this.results.backend.performance = perfResult.success;
      }

      // Skip load tests in normal runs (too resource intensive)
      this.log('INFO', 'Skipping load tests (run separately with scripts/run-load-tests.sh)');
      this.results.backend.load = null;

    } catch (error) {
      this.log('ERROR', `Backend tests failed: ${error.message}`);
      this.results.backend.unit = false;
      this.results.backend.integration = false;
      this.results.backend.performance = false;
    } finally {
      process.chdir(ROOT_DIR);
    }
  }

  async validateTestInfrastructure() {
    this.log('INFO', '=== Validating Test Infrastructure ===');
    
    try {
      const ValidatorClass = require('./validate-test-environment.js');
      const validator = new ValidatorClass();
      const isValid = await validator.run();
      return isValid;
    } catch (error) {
      this.log('ERROR', `Infrastructure validation failed: ${error.message}`);
      return false;
    }
  }

  generateTestReport() {
    this.log('INFO', '=== Test Suite Results ===');
    
    const formatResult = (result) => {
      if (result === true) return '✅ PASSED';
      if (result === false) return '❌ FAILED';
      return '⏸️ SKIPPED';
    };

    console.log('\n📊 Frontend Tests:');
    console.log(`  Unit Tests: ${formatResult(this.results.frontend.unit)}`);
    console.log(`  Integration Tests: ${formatResult(this.results.frontend.integration)}`);
    console.log(`  E2E Tests: ${formatResult(this.results.frontend.e2e)}`);

    console.log('\n📊 Backend Tests:');
    console.log(`  Unit Tests: ${formatResult(this.results.backend.unit)}`);
    console.log(`  Integration Tests: ${formatResult(this.results.backend.integration)}`);
    console.log(`  Performance Tests: ${formatResult(this.results.backend.performance)}`);
    console.log(`  Load Tests: ${formatResult(this.results.backend.load)}`);

    // Calculate overall results
    const allResults = [
      this.results.frontend.unit,
      this.results.frontend.integration,
      this.results.frontend.e2e,
      this.results.backend.unit,
      this.results.backend.integration,
      this.results.backend.performance,
      this.results.backend.load
    ];

    this.results.overall.passed = allResults.filter(r => r === true).length;
    this.results.overall.failed = allResults.filter(r => r === false).length;
    this.results.overall.skipped = allResults.filter(r => r === null).length;

    console.log('\n📈 Overall Summary:');
    console.log(`  ✅ Passed: ${this.results.overall.passed}`);
    console.log(`  ❌ Failed: ${this.results.overall.failed}`);
    console.log(`  ⏸️ Skipped: ${this.results.overall.skipped}`);

    const hasFailures = this.results.overall.failed > 0;
    const statusIcon = hasFailures ? '❌' : '✅';
    const statusText = hasFailures ? 'FAILED' : 'PASSED';
    
    console.log(`\n${statusIcon} Test Suite ${statusText}`);
    
    return !hasFailures;
  }

  async runFullTestSuite() {
    console.log('🚀 Starting comprehensive test suite...\n');
    
    // Validate infrastructure first
    const isInfraValid = await this.validateTestInfrastructure();
    if (!isInfraValid) {
      this.log('ERROR', 'Test infrastructure validation failed. Please fix issues before running tests.');
      return false;
    }

    // Run all test suites
    await this.runFrontendTests();
    await this.runBackendTests();
    
    // Generate final report
    return this.generateTestReport();
  }

  async runQuickTests() {
    console.log('⚡ Running quick test suite (unit tests only)...\n');
    
    try {
      // Frontend unit tests
      process.chdir(FRONTEND_DIR);
      this.log('INFO', 'Running frontend unit tests...');
      const frontendResult = await this.execCommand('npm test -- --passWithNoTests --watchAll=false');
      this.results.frontend.unit = frontendResult.success;
      
      // Backend unit tests
      process.chdir(BACKEND_DIR);
      this.log('INFO', 'Running backend unit tests...');
      const backendResult = await this.execCommand('python -m pytest tests/ -x --tb=short -q');
      this.results.backend.unit = backendResult.success;
      
    } catch (error) {
      this.log('ERROR', `Quick tests failed: ${error.message}`);
    } finally {
      process.chdir(ROOT_DIR);
    }
    
    return this.generateTestReport();
  }
}

// CLI interface
if (require.main === module) {
  const runner = new TestSuiteRunner();
  const mode = process.argv[2] || 'full';
  
  let testPromise;
  switch (mode) {
    case 'quick':
      testPromise = runner.runQuickTests();
      break;
    case 'frontend':
      testPromise = runner.runFrontendTests().then(() => runner.generateTestReport());
      break;
    case 'backend':
      testPromise = runner.runBackendTests().then(() => runner.generateTestReport());
      break;
    case 'validate':
      testPromise = runner.validateTestInfrastructure();
      break;
    case 'full':
    default:
      testPromise = runner.runFullTestSuite();
      break;
  }
  
  testPromise
    .then(success => {
      console.log(`\n🏁 Test suite completed. Exit code: ${success ? 0 : 1}`);
      process.exit(success ? 0 : 1);
    })
    .catch(error => {
      console.error('Test suite failed with error:', error);
      process.exit(1);
    });
}

module.exports = TestSuiteRunner;
