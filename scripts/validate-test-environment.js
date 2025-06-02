#!/usr/bin/env node

/**
 * Test Environment Validation Script
 * Validates that all test infrastructure components are properly configured
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const ROOT_DIR = path.join(__dirname, '..');
const FRONTEND_DIR = path.join(ROOT_DIR, 'frontend');
const BACKEND_DIR = path.join(ROOT_DIR, 'backend');

class TestEnvironmentValidator {
  constructor() {
    this.errors = [];
    this.warnings = [];
    this.successes = [];
  }

  log(type, message) {
    const timestamp = new Date().toISOString();
    const colorMap = {
      'ERROR': '\x1b[31m',
      'WARNING': '\x1b[33m',
      'SUCCESS': '\x1b[32m',
      'INFO': '\x1b[36m'
    };
    const reset = '\x1b[0m';
    console.log(`${colorMap[type]}[${timestamp}] ${type}: ${message}${reset}`);
    
    if (type === 'ERROR') this.errors.push(message);
    if (type === 'WARNING') this.warnings.push(message);
    if (type === 'SUCCESS') this.successes.push(message);
  }

  checkFileExists(filePath, description) {
    if (fs.existsSync(filePath)) {
      this.log('SUCCESS', `✓ ${description}: ${path.relative(ROOT_DIR, filePath)}`);
      return true;
    } else {
      this.log('ERROR', `✗ Missing ${description}: ${path.relative(ROOT_DIR, filePath)}`);
      return false;
    }
  }

  checkDirectoryExists(dirPath, description) {
    if (fs.existsSync(dirPath) && fs.statSync(dirPath).isDirectory()) {
      this.log('SUCCESS', `✓ ${description}: ${path.relative(ROOT_DIR, dirPath)}`);
      return true;
    } else {
      this.log('ERROR', `✗ Missing ${description}: ${path.relative(ROOT_DIR, dirPath)}`);
      return false;
    }
  }

  checkPackageJsonDependency(packageJsonPath, dependency, description) {
    try {
      const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
      const hasInDeps = packageJson.dependencies && packageJson.dependencies[dependency];
      const hasInDevDeps = packageJson.devDependencies && packageJson.devDependencies[dependency];
      
      if (hasInDeps || hasInDevDeps) {
        this.log('SUCCESS', `✓ ${description} dependency found: ${dependency}`);
        return true;
      } else {
        this.log('ERROR', `✗ Missing ${description} dependency: ${dependency}`);
        return false;
      }
    } catch (error) {
      this.log('ERROR', `✗ Could not read package.json: ${error.message}`);
      return false;
    }
  }

  checkPythonRequirement(requirementsPath, requirement, description) {
    try {
      const requirements = fs.readFileSync(requirementsPath, 'utf8');
      if (requirements.includes(requirement)) {
        this.log('SUCCESS', `✓ ${description} requirement found: ${requirement}`);
        return true;
      } else {
        this.log('ERROR', `✗ Missing ${description} requirement: ${requirement}`);
        return false;
      }
    } catch (error) {
      this.log('ERROR', `✗ Could not read requirements.txt: ${error.message}`);
      return false;
    }
  }

  validateFrontendInfrastructure() {
    this.log('INFO', '=== Validating Frontend Test Infrastructure ===');
    
    // Check package.json exists and has test dependencies
    const frontendPackageJson = path.join(FRONTEND_DIR, 'package.json');
    this.checkFileExists(frontendPackageJson, 'Frontend package.json');
    
    // Check Playwright dependencies
    this.checkPackageJsonDependency(frontendPackageJson, '@playwright/test', 'Playwright test framework');
    this.checkPackageJsonDependency(frontendPackageJson, 'axe-playwright', 'Accessibility testing');
    
    // Check Jest dependencies
    this.checkPackageJsonDependency(frontendPackageJson, 'jest', 'Jest testing framework');
    this.checkPackageJsonDependency(frontendPackageJson, '@testing-library/react', 'React Testing Library');
    
    // Check configuration files
    this.checkFileExists(path.join(FRONTEND_DIR, 'playwright.config.ts'), 'Playwright configuration');
    this.checkFileExists(path.join(FRONTEND_DIR, 'jest.config.js'), 'Jest configuration');
    
    // Check test directories
    this.checkDirectoryExists(path.join(FRONTEND_DIR, 'src', '__tests__'), 'Unit tests directory');
    this.checkDirectoryExists(path.join(FRONTEND_DIR, 'src', 'e2e'), 'E2E tests directory');
    
    // Check specific test files
    this.checkFileExists(
      path.join(FRONTEND_DIR, 'src', 'e2e', 'interview-prompts.spec.ts'),
      'Interview prompts E2E test'
    );
  }

  validateBackendInfrastructure() {
    this.log('INFO', '=== Validating Backend Test Infrastructure ===');
    
    // Check requirements.txt
    const requirementsPath = path.join(BACKEND_DIR, 'requirements.txt');
    this.checkFileExists(requirementsPath, 'Backend requirements.txt');
    
    // Check Python test dependencies
    this.checkPythonRequirement(requirementsPath, 'pytest', 'PyTest framework');
    this.checkPythonRequirement(requirementsPath, 'locust', 'Load testing framework');
    this.checkPythonRequirement(requirementsPath, 'faker', 'Test data generation');
    
    // Check test directories
    this.checkDirectoryExists(path.join(BACKEND_DIR, 'tests'), 'Backend tests directory');
    this.checkDirectoryExists(path.join(BACKEND_DIR, 'tests', 'factories'), 'Test factories directory');
    this.checkDirectoryExists(path.join(BACKEND_DIR, 'tests', 'load'), 'Load tests directory');
    this.checkDirectoryExists(path.join(BACKEND_DIR, 'tests', 'performance'), 'Performance tests directory');
    
    // Check specific test files
    this.checkFileExists(
      path.join(BACKEND_DIR, 'tests', 'factories', 'models.py'),
      'Test data factories'
    );
    this.checkFileExists(
      path.join(BACKEND_DIR, 'tests', 'load', 'locustfile.py'),
      'Locust load test configuration'
    );
    this.checkFileExists(
      path.join(BACKEND_DIR, 'scripts', 'test_data_manager.py'),
      'Test data management script'
    );
  }

  validateCIConfiguration() {
    this.log('INFO', '=== Validating CI/CD Configuration ===');
    
    const githubDir = path.join(ROOT_DIR, '.github', 'workflows');
    this.checkDirectoryExists(githubDir, 'GitHub workflows directory');
    
    // Check workflow files
    this.checkFileExists(
      path.join(githubDir, 'test-suite.yml'),
      'Test suite workflow'
    );
    this.checkFileExists(
      path.join(githubDir, 'deploy-staging.yml'),
      'Staging deployment workflow'
    );
    this.checkFileExists(
      path.join(githubDir, 'deploy-production.yml'),
      'Production deployment workflow'
    );
  }

  validateDocumentation() {
    this.log('INFO', '=== Validating Test Documentation ===');
    
    const docsDir = path.join(ROOT_DIR, 'docs', 'testing');
    this.checkDirectoryExists(docsDir, 'Testing documentation directory');
    
    // Check documentation files
    this.checkFileExists(path.join(docsDir, 'README.md'), 'Main testing README');
    this.checkFileExists(path.join(docsDir, 'setup-guide.md'), 'Setup guide');
    this.checkFileExists(path.join(docsDir, 'best-practices.md'), 'Best practices guide');
    this.checkFileExists(path.join(docsDir, 'cicd-integration.md'), 'CI/CD integration guide');
    this.checkFileExists(path.join(docsDir, 'test-data-management.md'), 'Test data management guide');
  }

  async validateNodeModules() {
    this.log('INFO', '=== Validating Node Dependencies ===');
    
    try {
      process.chdir(FRONTEND_DIR);
      const nodeModulesExists = fs.existsSync(path.join(FRONTEND_DIR, 'node_modules'));
      
      if (!nodeModulesExists) {
        this.log('WARNING', 'node_modules not found, dependencies may need to be installed');
        return;
      }
      
      // Check if Playwright is installed
      const playwrightPath = path.join(FRONTEND_DIR, 'node_modules', '@playwright', 'test');
      if (fs.existsSync(playwrightPath)) {
        this.log('SUCCESS', '✓ Playwright is installed');
      } else {
        this.log('WARNING', 'Playwright may need to be installed (run: npm install)');
      }
      
    } catch (error) {
      this.log('WARNING', `Could not validate Node dependencies: ${error.message}`);
    } finally {
      process.chdir(ROOT_DIR);
    }
  }

  generateReport() {
    this.log('INFO', '=== Test Environment Validation Report ===');
    
    console.log(`\n📊 Summary:`);
    console.log(`✓ Successes: ${this.successes.length}`);
    console.log(`⚠️  Warnings: ${this.warnings.length}`);
    console.log(`❌ Errors: ${this.errors.length}`);
    
    if (this.errors.length > 0) {
      console.log(`\n❌ Critical Issues to Fix:`);
      this.errors.forEach((error, index) => {
        console.log(`${index + 1}. ${error}`);
      });
    }
    
    if (this.warnings.length > 0) {
      console.log(`\n⚠️  Warnings to Address:`);
      this.warnings.forEach((warning, index) => {
        console.log(`${index + 1}. ${warning}`);
      });
    }
    
    if (this.errors.length === 0) {
      this.log('SUCCESS', '🎉 Test environment validation completed successfully!');
      console.log(`\n✅ Next Steps:`);
      console.log(`1. Install dependencies: cd frontend && npm install`);
      console.log(`2. Install Playwright browsers: npm run playwright:install`);
      console.log(`3. Install Python dependencies: cd backend && pip install -r requirements.txt`);
      console.log(`4. Run test suites to verify everything works`);
      return true;
    } else {
      this.log('ERROR', '❌ Test environment validation failed. Please fix the issues above.');
      return false;
    }
  }

  async run() {
    console.log('🔍 Starting test environment validation...\n');
    
    this.validateFrontendInfrastructure();
    this.validateBackendInfrastructure();
    this.validateCIConfiguration();
    this.validateDocumentation();
    await this.validateNodeModules();
    
    return this.generateReport();
  }
}

// Run validation if called directly
if (require.main === module) {
  const validator = new TestEnvironmentValidator();
  validator.run().then(success => {
    process.exit(success ? 0 : 1);
  }).catch(error => {
    console.error('Validation failed with error:', error);
    process.exit(1);
  });
}

module.exports = TestEnvironmentValidator;
