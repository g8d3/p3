#!/usr/bin/env python3
"""
API Benchmark Script for ZAI and OpenCode GO
Evaluates model availability, latency, throughput, and capabilities
"""

import os
import time
import json
import requests
import statistics
from datetime import datetime
from typing import Dict, List, Any, Optional

class APIEvaluator:
    def __init__(self):
        self.zai_api_key = os.getenv('ZAI_API_KEY')
        self.opencode_go_api_key = os.getenv('OPENCODE_GO_API_KEY')
        
        if not self.zai_api_key:
            raise ValueError("ZAI_API_KEY environment variable not set")
        if not self.opencode_go_api_key:
            raise ValueError("OPENCODE_GO_API_KEY environment variable not set")
        
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'zai': {},
            'opencode_go': {}
        }
        
        self.test_prompts = [
            "Hello, how are you today?",
            "What is the capital of France?",
            "Explain quantum computing in simple terms.",
            "Write a short poem about artificial intelligence.",
            "Describe a beautiful sunset using vivid language."
        ]
        
        self.vision_test_prompt = "Describe this image: https://images.unsplash.com/photo-1506748686214-e9df14d4d9d0?w=400"
    
    def make_api_call(self, api_name: str, endpoint: str, payload: Dict, headers: Dict, timeout: int = 30) -> Dict:
        """Make API call and measure performance"""
        start_time = time.time()
        try:
            response = requests.post(endpoint, json=payload, headers=headers, timeout=timeout)
            latency = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            if response.status_code == 200:
                data = response.json()
                tokens_used = data.get('usage', {}).get('total_tokens', 0)
                cost = self.calculate_cost(api_name, payload.get('model', ''), tokens_used)
                
                return {
                    'success': True,
                    'latency_ms': round(latency, 2),
                    'tokens_used': tokens_used,
                    'cost': cost,
                    'response_time': latency,
                    'tokens_per_second': round((tokens_used / latency) * 1000, 2) if latency > 0 else 0,
                    'data': data,
                    'status_code': response.status_code
                }
            else:
                return {
                    'success': False,
                    'latency_ms': round(latency, 2),
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'status_code': response.status_code
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'latency_ms': timeout * 1000,
                'error': 'Request timeout'
            }
        except Exception as e:
            return {
                'success': False,
                'latency_ms': (time.time() - start_time) * 1000,
                'error': str(e)
            }
    
    def calculate_cost(self, api_name: str, model: str, tokens: int) -> float:
        """Calculate approximate cost for API usage"""
        # Rough cost estimates per 1K tokens (these should be updated based on actual pricing)
        pricing = {
            'zai': {
                'gpt-3.5-turbo': 0.0015,
                'gpt-4': 0.03,
                'claude-3-haiku': 0.0025,
                'claude-3-sonnet': 0.015,
                'claude-3-opus': 0.15,
            },
            'opencode_go': {
                'gpt-3.5-turbo': 0.0015,
                'gpt-4': 0.03,
                'gemini-pro': 0.00125,
                'gemini-ultra': 0.05,
            }
        }
        
        # Default pricing if model not found
        default_price = 0.01
        price_per_1k = pricing.get(api_name, {}).get(model, default_price)
        return round((tokens / 1000) * price_per_1k, 6)
    
    def get_zai_models(self) -> List[str]:
        """Get available ZAI models"""
        try:
            headers = {'Authorization': f'Bearer {self.zai_api_key}'}
            response = requests.get('https://api.zai.chat/v1/models', headers=headers, timeout=10)
            if response.status_code == 200:
                models_data = response.json()
                return [model['id'] for model in models_data.get('data', [])]
            return []
        except:
            return []
    
    def get_opencode_go_models(self) -> List[str]:
        """Get available OpenCode GO models"""
        try:
            headers = {'Authorization': f'Bearer {self.opencode_go_api_key}'}
            response = requests.get('https://api.opencodego.com/v1/models', headers=headers, timeout=10)
            if response.status_code == 200:
                models_data = response.json()
                return [model['id'] for model in models_data.get('data', [])]
            return []
        except:
            return []
    
    def test_model_capabilities(self, api_name: str, model: str) -> Dict[str, Any]:
        """Test if model supports vision and other capabilities"""
        capabilities = {
            'text_completion': False,
            'vision': False,
            'json_mode': False,
            'function_calling': False
        }
        
        # Test text completion
        text_payload = {
            'model': model,
            'messages': [{'role': 'user', 'content': 'Hello, test message.'}],
            'max_tokens': 10
        }
        
        headers = {'Authorization': f'Bearer {self.zai_api_key}' if api_name == 'zai' else f'Bearer {self.opencode_go_api_key}'}
        endpoint = 'https://api.zai.chat/v1/chat/completions' if api_name == 'zai' else 'https://api.opencodego.com/v1/chat/completions'
        
        result = self.make_api_call(api_name, endpoint, text_payload, headers)
        if result['success']:
            capabilities['text_completion'] = True
        
        # Test vision (if supported)
        vision_payload = {
            'model': model,
            'messages': [{'role': 'user', 'content': [{"type": "text", "text": "What do you see?"}, {"type": "image_url", "image_url": {"url": "https://via.placeholder.com/150"}}]}],
            'max_tokens': 50
        }
        
        vision_result = self.make_api_call(api_name, endpoint, vision_payload, headers)
        if vision_result['success']:
            capabilities['vision'] = True
        
        return capabilities
    
    def benchmark_model(self, api_name: str, model: str, num_tests: int = 3) -> Dict[str, Any]:
        """Benchmark a single model with multiple tests"""
        headers = {'Authorization': f'Bearer {self.zai_api_key}' if api_name == 'zai' else f'Bearer {self.opencode_go_api_key}'}
        endpoint = 'https://api.zai.chat/v1/chat/completions' if api_name == 'zai' else 'https://api.opencodego.com/v1/chat/completions'
        
        latencies = []
        tokens_per_second = []
        costs = []
        successes = 0
        
        test_results = []
        
        for i, prompt in enumerate(self.test_prompts[:num_tests]):
            payload = {
                'model': model,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 100
            }
            
            result = self.make_api_call(api_name, endpoint, payload, headers)
            test_results.append({
                'test': i + 1,
                'prompt': prompt,
                'result': result
            })
            
            if result['success']:
                successes += 1
                latencies.append(result['latency_ms'])
                tokens_per_second.append(result['tokens_per_second'])
                costs.append(result['cost'])
        
        return {
            'model': model,
            'total_tests': num_tests,
            'successful_tests': successes,
            'success_rate': (successes / num_tests) * 100,
            'avg_latency_ms': round(statistics.mean(latencies), 2) if latencies else 0,
            'median_latency_ms': round(statistics.median(latencies), 2) if latencies else 0,
            'min_latency_ms': min(latencies) if latencies else 0,
            'max_latency_ms': max(latencies) if latencies else 0,
            'avg_tokens_per_second': round(statistics.mean(tokens_per_second), 2) if tokens_per_second else 0,
            'avg_cost_per_test': round(statistics.mean(costs), 6) if costs else 0,
            'total_cost': round(sum(costs), 6),
            'test_results': test_results,
            'timestamp': datetime.now().isoformat()
        }
    
    def evaluate_all_models(self):
        """Evaluate all available models from both APIs"""
        print("🚀 Starting API Evaluation...")
        print("=" * 60)
        
        # Get available models
        zai_models = self.get_zai_models()
        opencode_models = self.get_opencode_go_models()
        
        print(f"📋 ZAI Models Available: {len(zai_models)}")
        for model in zai_models:
            print(f"   - {model}")
        
        print(f"\n📋 OpenCode GO Models Available: {len(opencode_models)}")
        for model in opencode_models:
            print(f"   - {model}")
        
        # Benchmark ZAI models
        if zai_models:
            print(f"\n🔍 Benchmarking ZAI Models...")
            self.results['zai'] = {
                'available_models': zai_models,
                'model_results': []
            }
            
            for model in zai_models:
                print(f"\n📊 Testing {model}...")
                benchmark = self.benchmark_model('zai', model)
                self.results['zai']['model_results'].append(benchmark)
        
        # Benchmark OpenCode GO models
        if opencode_models:
            print(f"\n🔍 Benchmarking OpenCode GO Models...")
            self.results['opencode_go'] = {
                'available_models': opencode_models,
                'model_results': []
            }
            
            for model in opencode_models:
                print(f"\n📊 Testing {model}...")
                benchmark = self.benchmark_model('opencode_go', model)
                self.results['opencode_go']['model_results'].append(benchmark)
        
        # Generate summary
        self.generate_summary()
    
    def generate_summary(self):
        """Generate and display evaluation summary"""
        print("\n" + "=" * 60)
        print("📈 EVALUATION SUMMARY")
        print("=" * 60)
        
        # ZAI Summary
        if self.results['zai']:
            print(f"\n🔥 ZAI API Results:")
            zai_results = self.results['zai']['model_results']
            
            if zai_results:
                best_latency = min(zai_results, key=lambda x: x['avg_latency_ms'])
                best_throughput = max(zai_results, key=lambda x: x['avg_tokens_per_second'])
                best_reliability = max(zai_results, key=lambda x: x['success_rate'])
                
                print(f"   ⚡ Best Latency: {best_latency['model']} ({best_latency['avg_latency_ms']}ms)")
                print(f"   🚀 Best Throughput: {best_throughput['model']} ({best_throughput['avg_tokens_per_second']} tokens/sec)")
                print(f"   🛡️ Best Reliability: {best_reliability['model']} ({best_reliability['success_rate']:.1f}%)")
                
                total_zai_cost = sum(r['total_cost'] for r in zai_results)
                avg_zai_latency = sum(r['avg_latency_ms'] for r in zai_results) / len(zai_results)
                avg_zai_success = sum(r['success_rate'] for r in zai_results) / len(zai_results)
                
                print(f"   💰 Total ZAI Cost: ${total_zai_cost:.6f}")
                print(f"   📊 Average Latency: {avg_zai_latency:.2f}ms")
                print(f"   📊 Average Success Rate: {avg_zai_success:.1f}%")
        
        # OpenCode GO Summary
        if self.results['opencode_go']:
            print(f"\n🔥 OpenCode GO API Results:")
            opencode_results = self.results['opencode_go']['model_results']
            
            if opencode_results:
                best_latency = min(opencode_results, key=lambda x: x['avg_latency_ms'])
                best_throughput = max(opencode_results, key=lambda x: x['avg_tokens_per_second'])
                best_reliability = max(opencode_results, key=lambda x: x['success_rate'])
                
                print(f"   ⚡ Best Latency: {best_latency['model']} ({best_latency['avg_latency_ms']}ms)")
                print(f"   🚀 Best Throughput: {best_throughput['model']} ({best_throughput['avg_tokens_per_second']} tokens/sec)")
                print(f"   🛡️ Best Reliability: {best_reliability['model']} ({best_reliability['success_rate']:.1f}%)")
                
                total_opencode_cost = sum(r['total_cost'] for r in opencode_results)
                avg_opencode_latency = sum(r['avg_latency_ms'] for r in opencode_results) / len(opencode_results)
                avg_opencode_success = sum(r['success_rate'] for r in opencode_results) / len(opencode_results)
                
                print(f"   💰 Total OpenCode Cost: ${total_opencode_cost:.6f}")
                print(f"   📊 Average Latency: {avg_opencode_latency:.2f}ms")
                print(f"   📊 Average Success Rate: {avg_opencode_success:.1f}%")
        
        # Overall comparison
        print(f"\n🆚 OVERALL COMPARISON:")
        
        if self.results['zai'] and self.results['opencode_go']:
            zai_models = self.results['zai']['model_results']
            opencode_models = self.results['opencode_go']['model_results']
            
            zai_avg_latency = sum(r['avg_latency_ms'] for r in zai_models) / len(zai_models)
            opencode_avg_latency = sum(r['avg_latency_ms'] for r in opencode_models) / len(opencode_models)
            
            zai_avg_cost = sum(r['avg_cost_per_test'] for r in zai_models) / len(zai_models)
            opencode_avg_cost = sum(r['avg_cost_per_test'] for r in opencode_models) / len(opencode_models)
            
            zai_success_rate = sum(r['success_rate'] for r in zai_models) / len(zai_models)
            opencode_success_rate = sum(r['success_rate'] for r in opencode_models) / len(opencode_models)
            
            print(f"   Latency - ZAI: {zai_avg_latency:.2f}ms vs OpenCode GO: {opencode_avg_latency:.2f}ms")
            print(f"   Cost per Test - ZAI: ${zai_avg_cost:.6f} vs OpenCode GO: ${opencode_avg_cost:.6f}")
            print(f"   Success Rate - ZAI: {zai_success_rate:.1f}% vs OpenCode GO: {opencode_success_rate:.1f}%")
        
        # Save detailed results
        self.save_results()
    
    def save_results(self):
        """Save detailed results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"api_benchmark_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {filename}")

def main():
    try:
        evaluator = APIEvaluator()
        evaluator.evaluate_all_models()
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("Please ensure both ZAI_API_KEY and OPENCODE_GO_API_KEY environment variables are set.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()