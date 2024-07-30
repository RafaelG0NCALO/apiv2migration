import requests
from bs4 import BeautifulSoup
import json
import asyncio
import websockets
from aiohttp import web
import pandas as pd

base_url = ''

def get_page(url):
    print(f'Obtendo conteúdo da página: {url}')
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def check_url_status(url):
    print(f'Verificando status da URL: {url}')
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)  # Adiciona um timeout
        response.raise_for_status()
        return response.status_code
    except requests.RequestException as e:
        print(f'Erro ao verificar status da URL {url}: {e}')
        return None

def process_links(html):
    print('Processando links...')
    soup = BeautifulSoup(html, 'html.parser')
    records = []

    divs = soup.find_all('div', class_='paginas-internas')
    print(f'Encontradas {len(divs)} divs com a classe "paginas-internas".')
    for div in divs:
        links = div.find_all('a')
        for link in links:
            href = link.get('href', '')
            if href.lower().endswith(('.pdf', '.png', '.jpeg', '.jpg')):
                file_url = href if href.startswith('http') else base_url + href
                status_code = check_url_status(file_url)
                
                if status_code == 404:
                    records.append({'URL': file_url, 'Status': 'Erro 404'})
                    print(f'URL: {file_url} - Erro 404')
                elif status_code == 200:
                    records.append({'URL': file_url, 'Status': 'OK'})
                    print(f'URL: {file_url} - OK')
                else:
                    records.append({'URL': file_url, 'Status': f'Status inesperado: {status_code}'})
                    print(f'URL: {file_url} - Status inesperado: {status_code}')

    return records

def count_statuses(records):
    totals = {
        'total': len(records),
        'ok': sum(1 for record in records if record['Status'] == 'OK'),
        'error': sum(1 for record in records if record['Status'].startswith('Erro'))
    }
    return totals

def save_to_excel(records, filename='records.xlsx'):
    df = pd.DataFrame(records)
    df.to_excel(filename, index=False)
    print(f'Arquivo Excel salvo como {filename}')

async def handle_client(websocket, path):
    async for message in websocket:
        data = json.loads(message)
        url = data.get('url', '')
        print(f'URL recebida: {url}')

        try:
            html_content = get_page(url)
            records = process_links(html_content)
            totals = count_statuses(records)
            save_to_excel(records)  
            response = {
                'records': records,
                'url': url,
                'totals': totals 
            }
            await websocket.send(json.dumps(response))
        except Exception as e:
            await websocket.send(json.dumps({'error': str(e)}))

async def handle_download(request):
    filename = 'records.xlsx'
    return web.FileResponse(filename)

async def main():
    app = web.Application()
    app.router.add_get('/download', handle_download)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    
    async with websockets.serve(handle_client, "localhost", 8765):
        await asyncio.Future() 

if __name__ == "__main__":
    asyncio.run(main())
