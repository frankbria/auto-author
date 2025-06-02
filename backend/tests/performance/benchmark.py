#!/usr/bin/env python3
"""
Performance benchmarking script for Auto-Author API.

This script runs comprehensive performance tests and generates detailed reports
including response times, throughput, and resource utilization metrics.
"""

import asyncio
import aiohttp
import time
import statistics
import json
import sys
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import psutil
import argparse

@dataclass
class PerformanceMetrics:
    """Container for performance test results."""
    test_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    requests_per_second: float
    total_duration: float
    error_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class PerformanceBenchmark:
    """Performance benchmark runner for Auto-Author API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", auth_token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.session = None
        
    async def setup_session(self):
        """Setup HTTP session with authentication."""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        self.session = aiohttp.ClientSession(
            headers=headers,
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30)
        )
    
    async def cleanup_session(self):
        """Cleanup HTTP session."""
        if self.session:
            await self.session.close()
    
    async def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a single HTTP request and measure performance."""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            if method.upper() == 'GET':
                async with self.session.get(url) as response:
                    content = await response.json() if response.content_type == 'application/json' else await response.text()
                    end_time = time.time()
                    
                    return {
                        'success': response.status < 400,
                        'status_code': response.status,
                        'response_time': (end_time - start_time) * 1000,  # Convert to ms
                        'content_length': len(str(content)),
                        'error': None
                    }
            
            elif method.upper() == 'POST':
                async with self.session.post(url, json=data) as response:
                    content = await response.json() if response.content_type == 'application/json' else await response.text()
                    end_time = time.time()
                    
                    return {
                        'success': response.status < 400,
                        'status_code': response.status,
                        'response_time': (end_time - start_time) * 1000,
                        'content_length': len(str(content)),
                        'error': None
                    }
        
        except Exception as e:
            end_time = time.time()
            return {
                'success': False,
                'status_code': 0,
                'response_time': (end_time - start_time) * 1000,
                'content_length': 0,
                'error': str(e)
            }
    
    async def run_concurrent_requests(self, method: str, endpoint: str, 
                                    concurrent_users: int, requests_per_user: int,
                                    data_generator=None) -> List[Dict[str, Any]]:
        """Run concurrent requests to simulate load."""
        
        async def user_requests():
            results = []
            for _ in range(requests_per_user):
                data = data_generator() if data_generator else None
                result = await self.make_request(method, endpoint, data)
                results.append(result)
            return results
        
        # Create tasks for concurrent users
        tasks = [user_requests() for _ in range(concurrent_users)]
        user_results = await asyncio.gather(*tasks)
        
        # Flatten results
        all_results = []
        for user_result in user_results:
            all_results.extend(user_result)
        
        return all_results
    
    def calculate_metrics(self, results: List[Dict[str, Any]], test_name: str, duration: float) -> PerformanceMetrics:
        """Calculate performance metrics from test results."""
        total_requests = len(results)
        successful_requests = sum(1 for r in results if r['success'])
        failed_requests = total_requests - successful_requests
        
        response_times = [r['response_time'] for r in results]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        else:
            avg_response_time = min_response_time = max_response_time = p95_response_time = 0
        
        requests_per_second = total_requests / duration if duration > 0 else 0
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        
        return PerformanceMetrics(
            test_name=test_name,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            requests_per_second=requests_per_second,
            total_duration=duration,
            error_rate=error_rate
        )
    
    # Specific test methods
    
    async def test_health_check(self, concurrent_users: int = 10, requests_per_user: int = 10) -> PerformanceMetrics:
        """Test health check endpoint performance."""
        print(f"Running health check test with {concurrent_users} users, {requests_per_user} requests each...")
        
        start_time = time.time()
        results = await self.run_concurrent_requests('GET', '/health', concurrent_users, requests_per_user)
        end_time = time.time()
        
        return self.calculate_metrics(results, 'Health Check', end_time - start_time)
    
    async def test_question_generation(self, concurrent_users: int = 5, requests_per_user: int = 5) -> PerformanceMetrics:
        """Test question generation endpoint performance."""
        print(f"Running question generation test with {concurrent_users} users, {requests_per_user} requests each...")
        
        def generate_question_data():
            return {
                "chapter_id": "test-chapter-1",
                "question_count": 5,
                "question_types": ["open-ended", "multiple-choice"]
            }
        
        start_time = time.time()
        results = await self.run_concurrent_requests(
            'POST', 
            '/api/chapters/test-chapter-1/questions/generate',
            concurrent_users, 
            requests_per_user,
            generate_question_data
        )
        end_time = time.time()
        
        return self.calculate_metrics(results, 'Question Generation', end_time - start_time)
    
    async def test_response_submission(self, concurrent_users: int = 10, requests_per_user: int = 10) -> PerformanceMetrics:
        """Test response submission endpoint performance."""
        print(f"Running response submission test with {concurrent_users} users, {requests_per_user} requests each...")
        
        def generate_response_data():
            return {
                "question_id": f"test-question-{time.time()}",
                "content": "This is a test response for performance benchmarking.",
                "time_taken": 120
            }
        
        start_time = time.time()
        results = await self.run_concurrent_requests(
            'POST',
            '/api/responses',
            concurrent_users,
            requests_per_user,
            generate_response_data
        )
        end_time = time.time()
        
        return self.calculate_metrics(results, 'Response Submission', end_time - start_time)
    
    async def test_chapter_operations(self, concurrent_users: int = 5, requests_per_user: int = 5) -> PerformanceMetrics:
        """Test chapter CRUD operations performance."""
        print(f"Running chapter operations test with {concurrent_users} users, {requests_per_user} requests each...")
        
        def generate_chapter_data():
            return {
                "title": f"Performance Test Chapter {time.time()}",
                "content": "This is test content for performance benchmarking. " * 50,
                "book_id": "test-book-1",
                "order": 1
            }
        
        start_time = time.time()
        results = await self.run_concurrent_requests(
            'POST',
            '/api/chapters',
            concurrent_users,
            requests_per_user,
            generate_chapter_data
        )
        end_time = time.time()
        
        return self.calculate_metrics(results, 'Chapter Operations', end_time - start_time)
    
    async def test_dashboard_load(self, concurrent_users: int = 20, requests_per_user: int = 10) -> PerformanceMetrics:
        """Test dashboard loading performance."""
        print(f"Running dashboard load test with {concurrent_users} users, {requests_per_user} requests each...")
        
        start_time = time.time()
        results = await self.run_concurrent_requests('GET', '/api/dashboard', concurrent_users, requests_per_user)
        end_time = time.time()
        
        return self.calculate_metrics(results, 'Dashboard Load', end_time - start_time)

class SystemMonitor:
    """Monitor system resources during performance tests."""
    
    def __init__(self):
        self.monitoring = False
        self.metrics = []
    
    def start_monitoring(self):
        """Start monitoring system resources."""
        self.monitoring = True
        self.metrics = []
        
        async def monitor():
            while self.monitoring:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                self.metrics.append({
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_used_gb': memory.used / (1024**3),
                    'disk_percent': disk.percent
                })
                
                await asyncio.sleep(1)
        
        asyncio.create_task(monitor())
    
    def stop_monitoring(self):
        """Stop monitoring and return collected metrics."""
        self.monitoring = False
        return self.metrics
    
    def get_resource_summary(self) -> Dict[str, Any]:
        """Get summary of resource usage during monitoring."""
        if not self.metrics:
            return {}
        
        cpu_values = [m['cpu_percent'] for m in self.metrics]
        memory_values = [m['memory_percent'] for m in self.metrics]
        
        return {
            'avg_cpu_percent': statistics.mean(cpu_values),
            'max_cpu_percent': max(cpu_values),
            'avg_memory_percent': statistics.mean(memory_values),
            'max_memory_percent': max(memory_values),
            'peak_memory_used_gb': max(m['memory_used_gb'] for m in self.metrics)
        }

class PerformanceReporter:
    """Generate performance test reports."""
    
    @staticmethod
    def print_metrics(metrics: PerformanceMetrics):
        """Print performance metrics to console."""
        print(f"\n{'='*50}")
        print(f"Test: {metrics.test_name}")
        print(f"{'='*50}")
        print(f"Total Requests: {metrics.total_requests}")
        print(f"Successful: {metrics.successful_requests}")
        print(f"Failed: {metrics.failed_requests}")
        print(f"Error Rate: {metrics.error_rate:.2f}%")
        print(f"Duration: {metrics.total_duration:.2f}s")
        print(f"Requests/sec: {metrics.requests_per_second:.2f}")
        print(f"\nResponse Times (ms):")
        print(f"  Average: {metrics.avg_response_time:.2f}")
        print(f"  Min: {metrics.min_response_time:.2f}")
        print(f"  Max: {metrics.max_response_time:.2f}")
        print(f"  95th percentile: {metrics.p95_response_time:.2f}")
    
    @staticmethod
    def save_json_report(metrics_list: List[PerformanceMetrics], filename: str):
        """Save performance metrics to JSON file."""
        report_data = {
            'test_run_timestamp': time.time(),
            'test_summary': {
                'total_tests': len(metrics_list),
                'total_requests': sum(m.total_requests for m in metrics_list),
                'total_failures': sum(m.failed_requests for m in metrics_list),
                'overall_error_rate': sum(m.failed_requests for m in metrics_list) / sum(m.total_requests for m in metrics_list) * 100 if metrics_list else 0
            },
            'test_results': [m.to_dict() for m in metrics_list]
        }
        
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\nReport saved to: {filename}")
    
    @staticmethod
    def save_csv_report(metrics_list: List[PerformanceMetrics], filename: str):
        """Save performance metrics to CSV file."""
        import csv
        
        fieldnames = [
            'test_name', 'total_requests', 'successful_requests', 'failed_requests',
            'avg_response_time', 'min_response_time', 'max_response_time', 'p95_response_time',
            'requests_per_second', 'total_duration', 'error_rate'
        ]
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for metrics in metrics_list:
                writer.writerow(metrics.to_dict())
        
        print(f"CSV report saved to: {filename}")

async def run_performance_suite(base_url: str, auth_token: Optional[str] = None):
    """Run complete performance test suite."""
    benchmark = PerformanceBenchmark(base_url, auth_token)
    monitor = SystemMonitor()
    
    await benchmark.setup_session()
    monitor.start_monitoring()
    
    try:
        print("Starting Auto-Author Performance Benchmark Suite")
        print(f"Target URL: {base_url}")
        print("="*60)
        
        # Run all performance tests
        tests = []
        
        # Basic endpoint tests
        tests.append(await benchmark.test_health_check(10, 20))
        tests.append(await benchmark.test_dashboard_load(15, 10))
        
        # Core functionality tests
        tests.append(await benchmark.test_question_generation(5, 10))
        tests.append(await benchmark.test_response_submission(8, 15))
        tests.append(await benchmark.test_chapter_operations(5, 8))
        
        # Print results
        for test_metrics in tests:
            PerformanceReporter.print_metrics(test_metrics)
        
        # System resource summary
        resource_metrics = monitor.stop_monitoring()
        resource_summary = monitor.get_resource_summary()
        
        if resource_summary:
            print(f"\n{'='*50}")
            print("System Resource Usage")
            print(f"{'='*50}")
            print(f"Average CPU: {resource_summary['avg_cpu_percent']:.1f}%")
            print(f"Peak CPU: {resource_summary['max_cpu_percent']:.1f}%")
            print(f"Average Memory: {resource_summary['avg_memory_percent']:.1f}%")
            print(f"Peak Memory: {resource_summary['max_memory_percent']:.1f}%")
            print(f"Peak Memory Used: {resource_summary['peak_memory_used_gb']:.2f} GB")
        
        # Save reports
        timestamp = int(time.time())
        PerformanceReporter.save_json_report(tests, f"performance_report_{timestamp}.json")
        PerformanceReporter.save_csv_report(tests, f"performance_report_{timestamp}.csv")
        
        return tests
        
    finally:
        monitor.stop_monitoring()
        await benchmark.cleanup_session()

def main():
    """Main entry point for performance benchmark."""
    parser = argparse.ArgumentParser(description="Auto-Author Performance Benchmark")
    parser.add_argument('--url', default='http://localhost:8000', help='Base URL for API')
    parser.add_argument('--token', help='Authentication token')
    parser.add_argument('--quick', action='store_true', help='Run quick test suite')
    
    args = parser.parse_args()
    
    if args.quick:
        print("Running quick performance test...")
        # Reduced test parameters for quick testing
    
    try:
        asyncio.run(run_performance_suite(args.url, args.token))
    except KeyboardInterrupt:
        print("\nPerformance test interrupted by user.")
    except Exception as e:
        print(f"Error running performance tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
