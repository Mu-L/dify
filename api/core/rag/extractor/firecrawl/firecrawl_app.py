import os
import time

import requests


class FirecrawlApp:
    def __init__(self, api_key=None, base_url='https://api.firecrawl.dev'):
        self.api_key = api_key or os.getenv('FIRECRAWL_API_KEY')
        self.base_url = base_url or os.getenv('FIRECRAWL_BASE_URL')
        if self.api_key is None:
            raise ValueError('No API key provided')
    
    def scrape_url(self, url, params=None):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        json_data = {'url': url}
        if params:
            json_data.update(params)
        response = requests.post(
            f'{self.base_url}/v0/scrape',
            headers=headers,
            json=json_data
        )
        if response.status_code == 200:
            response = response.json()
            if response['success'] == True:
                return response['data']
            else:
                raise Exception(f'Failed to scrape URL. Error: {response["error"]}')
            
        elif response.status_code in [402, 409, 500]:
            error_message = response.json().get('error', 'Unknown error occurred')
            raise Exception(f'Failed to scrape URL. Status code: {response.status_code}. Error: {error_message}')
        else:
            raise Exception(f'Failed to scrape URL. Status code: {response.status_code}')
        
    def search(self, query, params=None):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        json_data = {'query': query}
        if params:
            json_data.update(params)
        response = requests.post(
            f'{self.base_url}/v0/search',
            headers=headers,
            json=json_data
        )
        if response.status_code == 200:
            response = response.json()
            if response['success'] == True:
                return response['data']
            else:
                raise Exception(f'Failed to search. Error: {response["error"]}')
            
        elif response.status_code in [402, 409, 500]:
            error_message = response.json().get('error', 'Unknown error occurred')
            raise Exception(f'Failed to search. Status code: {response.status_code}. Error: {error_message}')
        else:
            raise Exception(f'Failed to search. Status code: {response.status_code}')

    def crawl_url(self, url, params=None, wait_until_done=True, polling_interval=2, timeout=500):
        start_time = time.time()
        headers = self._prepare_headers()
        json_data = {'url': url}
        if params:
            json_data.update(params)
        response = self._post_request(f'{self.base_url}/v0/crawl', json_data, headers)
        if response.status_code == 200:
            job_id = response.json().get('jobId')
            if wait_until_done:
                while True:
                    elapsed_time = time.time() - start_time
                    if elapsed_time > timeout:
                        raise Exception('Firecrawl: Crawl job timed out.')
                    result = self._monitor_job_status(job_id, headers, polling_interval)
                    if result is not None:
                        return result
            else:
                return {'jobId': job_id}
        else:
            self._handle_error(response, 'start crawl job')


    def check_crawl_status(self, job_id):
        headers = self._prepare_headers()
        response = self._get_request(f'{self.base_url}/v0/crawl/status/{job_id}', headers)
        if response.status_code == 200:
            return response.json()
        else:
            self._handle_error(response, 'check crawl status')

    def _prepare_headers(self):
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

    def _post_request(self, url, data, headers, retries=3, backoff_factor=0.5):
        for attempt in range(retries):
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 502:
                time.sleep(backoff_factor * (2 ** attempt))
            else:
                return response
        return response

    def _get_request(self, url, headers, retries=3, backoff_factor=0.5):
        for attempt in range(retries):
            response = requests.get(url, headers=headers)
            if response.status_code == 502:
                time.sleep(backoff_factor * (2 ** attempt))
            else:
                return response
        return response
    
    def _monitor_job_status(self, job_id, headers, polling_interval):
        status_response = self._get_request(f'{self.base_url}/v0/crawl/status/{job_id}', headers)
        if status_response.status_code == 200:
            status_data = status_response.json()
            if status_data['status'] == 'completed':
                if 'data' in status_data:
                    return status_data['data']
                else:
                    raise Exception('Crawl job completed but no data was returned')
            elif status_data['status'] in ['active', 'paused', 'pending', 'queued']:
                time.sleep(max(polling_interval, 2))  # Wait for the specified polling_interval before checking again
            else:
                raise Exception(f'Crawl job failed or was stopped. Status: {status_data["status"]}')
        else:
            self._handle_error(status_response, 'check crawl status')

    def _handle_error(self, response, action):
        if response.status_code in [402, 409, 500]:
            error_message = response.json().get('error', 'Unknown error occurred')
            raise Exception(f'Failed to {action}. Status code: {response.status_code}. Error: {error_message}')
        else:
            raise Exception(f'Unexpected error occurred while trying to {action}. Status code: {response.status_code}')