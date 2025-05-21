import requests
from bs4 import BeautifulSoup
import os
import time
import re # Para limpar nomes de arquivos
from urllib.parse import urljoin # Para construir URLs absolutas

# Cabeçalho para simular um navegador e evitar bloqueios simples
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def _download_chapter_html(chapter_url: str) -> requests.Response | None:
    """
    Baixa o conteúdo HTML de uma URL de capítulo.
    Retorna o objeto de resposta da requisição ou None em caso de erro.
    """
    print(f"   Tentando baixar: {chapter_url}")
    try:
        response = requests.get(chapter_url, headers=HEADERS, timeout=15) # Timeout de 15s
        response.raise_for_status()  # Levanta um erro para códigos HTTP 4xx/5xx
        return response
    except requests.exceptions.HTTPError as http_err:
        print(f"   Erro HTTP ao baixar {chapter_url}: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"   Erro de conexão ao baixar {chapter_url}: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"   Timeout ao baixar {chapter_url}: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"   Erro geral ao baixar {chapter_url}: {req_err}")
    return None

def _parse_chapter_html(html_content: str, current_page_url: str) -> dict:
    """
    Analisa o HTML bruto de um capítulo e extrai título, conteúdo e URL do próximo capítulo.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Título do Capítulo
    # Tentativa 1: Pelo h1 específico no cabeçalho da ficção na página do capítulo
    title_tag = soup.select_one('div.fic-header h1.font-white.break-word')
    if not title_tag:
        # Tentativa 2: Pela tag <title> da página (mais robusto)
        page_title_tag = soup.find('title')
        if page_title_tag:
            # Ex: "Chapter Title - Story Name | Royal Road"
            # Pega a parte antes do primeiro " - "
            title = page_title_tag.text.split(' - ')[0].strip()
        else:
            title = "Título Desconhecido"
    else:
        title = title_tag.text.strip()

    # Conteúdo da História
    content_div = soup.find('div', class_='chapter-content')
    content_html = str(content_div) if content_div else "<p>Conteúdo não encontrado.</p>"
    
    # Link do Próximo Capítulo
    next_chapter_url = None
    next_link_tag = soup.find('link', rel='next')
    if next_link_tag and next_link_tag.get('href'):
        relative_url = next_link_tag['href']
        # Constrói a URL absoluta. urljoin lida com URLs base e relativas.
        # Se relative_url já for absoluta, urljoin a mantém.
        # Se current_page_url é 'https://www.royalroad.com/fiction/123/story/chapter/1'
        # e relative_url é '/fiction/123/story/chapter/2'
        # urljoin(current_page_url, relative_url) -> 'https://www.royalroad.com/fiction/123/story/chapter/2'
        next_chapter_url = urljoin(current_page_url, relative_url)
    else:
        # Fallback para o botão "Next Chapter" se o link rel="next" não for encontrado
        # Existem dois botões "Next", vamos pegar o primeiro que tenha "Next" e um href válido
        next_buttons = soup.select('a.btn.btn-primary')
        for button in next_buttons:
            if "Next" in button.text and button.get('href'):
                relative_url = button['href']
                if relative_url and relative_url != "#" and "javascript:void(0)" not in relative_url:
                    next_chapter_url = urljoin(current_page_url, relative_url)
                    break # Pega o primeiro link válido

    return {
        'title': title,
        'content_html': content_html,
        'next_chapter_url': next_chapter_url
    }

def _sanitize_filename(filename: str) -> str:
    """
    Remove caracteres inválidos de um nome de arquivo e o encurta se necessário.
    """
    # Remove caracteres que são problemáticos em nomes de arquivo
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
    # Substitui múltiplos espaços ou tabulações por um único sublinhado
    sanitized = re.sub(r'\s+', '_', sanitized)
    # Limita o comprimento para evitar nomes de arquivo excessivamente longos
    return sanitized[:100] # Mantém os primeiros 100 caracteres

def download_story(first_chapter_url: str, output_folder: str):
    """
    Baixa todos os capítulos de uma história da Royal Road, começando pela URL do primeiro capítulo.
    """
    if not os.path.exists(output_folder):
        print(f"Criando pasta de saída: {output_folder}")
        os.makedirs(output_folder, exist_ok=True)
    else:
        print(f"Usando pasta de saída existente: {output_folder}")

    current_chapter_url = first_chapter_url
    chapter_number = 1
    
    # Extrai o nome da história da URL para nomear a pasta de saída (opcional, mas útil)
    try:
        story_slug = first_chapter_url.split('/fiction/')[1].split('/')[1]
        story_output_folder = os.path.join(output_folder, _sanitize_filename(story_slug))
        if not os.path.exists(story_output_folder):
            os.makedirs(story_output_folder, exist_ok=True)
        print(f"Salvando capítulos em: {story_output_folder}")
    except IndexError:
        print("Não foi possível extrair o nome da história da URL, usando a pasta de saída principal.")
        story_output_folder = output_folder


    while current_chapter_url:
        print(f"\nBaixando capítulo {chapter_number}...")
        
        response = _download_chapter_html(current_chapter_url)
        if not response:
            print(f"Falha ao baixar o capítulo {chapter_number}. Tentando o próximo se houver URL.")
            # Poderíamos tentar novamente ou pular, por enquanto vamos parar se um capítulo falhar
            # Se você quiser continuar, precisaria de uma lógica para obter o próximo URL de outra forma ou pular.
            # Neste ponto, se response é None, não temos como obter o next_chapter_url facilmente
            # a menos que o usuário tenha fornecido uma lista de capítulos ou algo assim.
            # Por simplicidade, se uma página falhar, e não tivermos o next_chapter_url de antemão, paramos.
            # No entanto, o _parse_chapter_html ainda pode ser chamado se a falha não foi fatal
            # e queremos extrair o `next_chapter_url` mesmo se o conteúdo estiver incompleto.
            # Mas se `response` é None, não temos `response.text`.
            # Vamos assumir que, se o download falhar, paramos aqui.
            break

        chapter_data = _parse_chapter_html(response.text, current_chapter_url)
        
        title = chapter_data['title']
        content_html = chapter_data['content_html']
        next_url = chapter_data['next_chapter_url']

        print(f"   Título: {title}")

        # Sanitizar o título para usar como parte do nome do arquivo
        safe_title = _sanitize_filename(title)
        filename = f"capitulo_{chapter_number:03d}_{safe_title}.html"
        filepath = os.path.join(story_output_folder, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"\n")
                f.write(f"\n")
                f.write("<!DOCTYPE html>\n<html lang=\"pt-BR\">\n<head>\n")
                f.write(f"  <meta charset=\"UTF-8\">\n  <title>{title}</title>\n")
                f.write("  <style>body { font-family: sans-serif; margin: 20px; } .chapter-content { max-width: 800px; margin: 0 auto; }</style>\n")
                f.write("</head>\n<body>\n")
                f.write(f"<h1>{title}</h1>\n")
                f.write(content_html) # content_html já é uma string HTML
                f.write("\n</body>\n</html>")
            print(f"   Salvo em: {filepath}")
        except IOError as e:
            print(f"   ERRO ao salvar o arquivo {filepath}: {e}")
            # Decide se quer parar ou continuar para o próximo capítulo
            # Por enquanto, vamos continuar
        
        current_chapter_url = next_url
        
        if not current_chapter_url:
            print("\nFim da história alcançado ou próximo capítulo não encontrado.")
            break
            
        chapter_number += 1
        
        # Atraso para não sobrecarregar o servidor
        delay = 2 # segundos
        print(f"   Aguardando {delay} segundos antes do próximo capítulo...")
        time.sleep(delay)

    print("\nProcesso de download concluído.")

if __name__ == '__main__':
    # Teste rápido (opcional, geralmente isso iria no main.py)
    test_url = "https://www.royalroad.com/fiction/64503/primer-for-the-apocalypse/chapter/1346792/prologue-revised"
    test_output_folder = "downloaded_story_test"
    
    print(f"Iniciando teste de download para: {test_url}")
    download_story(test_url, test_output_folder)
    print("Teste concluído.")