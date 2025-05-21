import random
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

def _download_page_html(page_url: str) -> requests.Response | None:
    """
    Baixa o conteúdo HTML de uma URL.
    Retorna o objeto de resposta da requisição ou None em caso de erro.
    """
    print(f"   Tentando baixar: {page_url}")
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=15) # Timeout de 15s
        response.raise_for_status()  # Levanta um erro para códigos HTTP 4xx/5xx
        return response
    except requests.exceptions.HTTPError as http_err:
        print(f"   Erro HTTP ao baixar {page_url}: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"   Erro de conexão ao baixar {page_url}: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"   Timeout ao baixar {page_url}: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"   Erro geral ao baixar {page_url}: {req_err}")
    return None

def fetch_story_metadata_and_first_chapter(overview_url: str) -> dict | None:
    """
    Busca metadados da história (título, autor, URL do primeiro capítulo)
    a partir da página de visão geral da história.
    """
    print(f"Buscando metadados da página de visão geral: {overview_url}")
    response = _download_page_html(overview_url)
    if not response:
        print("   Falha ao baixar a página de visão geral.")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    metadata = {
        'first_chapter_url': None,
        'story_title': "Título Desconhecido",
        'author_name': "Autor Desconhecido",
        'story_slug': None
    }

    # Extrair URL do primeiro capítulo
    # Procurar pelo botão "Start Reading" ou similar que leve ao primeiro capítulo
    # <a href="/fiction/115305/pioneer-of-the-abyss-an-underwater-livestreamed/chapter/2251704/b1-chapter-1" class="btn btn-lg btn-primary">
    start_reading_link = soup.select_one('a.btn.btn-primary[href*="/chapter/"]')
    if start_reading_link and start_reading_link.get('href'):
        relative_url = start_reading_link['href']
        metadata['first_chapter_url'] = urljoin(overview_url, relative_url)
        print(f"   URL do primeiro capítulo encontrada: {metadata['first_chapter_url']}")
    else:
        print("   AVISO: URL do primeiro capítulo não encontrada na página de visão geral.")
        # Tenta encontrar na tabela de capítulos se o botão não existir
        first_chapter_row_link = soup.select_one('table#chapters tbody tr[data-url] a')
        if first_chapter_row_link and first_chapter_row_link.get('href'):
            relative_url = first_chapter_row_link['href']
            metadata['first_chapter_url'] = urljoin(overview_url, relative_url)
            print(f"   URL do primeiro capítulo (fallback da tabela) encontrada: {metadata['first_chapter_url']}")
        else:
            print("   ERRO CRÍTICO: Não foi possível encontrar a URL do primeiro capítulo.")
            return None # Essencial para continuar

    # Extrair título da história
    # <h1 class="font-white">Pioneer of the Abyss: An Underwater Livestreamed Isekai LitRPG</h1>
    title_tag = soup.select_one('div.fic-title h1.font-white')
    if title_tag:
        metadata['story_title'] = title_tag.text.strip()
        print(f"   Título da história encontrado: {metadata['story_title']}")
    else:
        # Fallback para a tag <title> da página
        page_title_tag = soup.find('title')
        if page_title_tag:
            # Ex: "Pioneer of the Abyss: An Underwater Livestreamed Isekai LitRPG | Royal Road"
            full_title = page_title_tag.text.strip()
            metadata['story_title'] = full_title.split('|')[0].strip() # Pega a parte antes do pipe
            print(f"   Título da história (fallback da tag title) encontrado: {metadata['story_title']}")
        else:
            print("   AVISO: Título da história não encontrado.")


    # Extrair nome do autor
    # <span><a href="/profile/102324" class="font-white">WolfShine</a></span>
    author_link = soup.select_one('div.fic-title h4 span a[href*="/profile/"]')
    if author_link:
        metadata['author_name'] = author_link.text.strip()
        print(f"   Nome do autor encontrado: {metadata['author_name']}")
    else:
        # Fallback: Tentar encontrar no schema JSON LD
        script_tag = soup.find('script', type='application/ld+json')
        if script_tag:
            try:
                import json
                json_data = json.loads(script_tag.string)
                if json_data.get('author') and json_data['author'].get('name'):
                    metadata['author_name'] = json_data['author']['name'].strip()
                    print(f"   Nome do autor (fallback do JSON-LD) encontrado: {metadata['author_name']}")
            except Exception as e:
                print(f"   AVISO: Erro ao parsear JSON-LD para nome do autor: {e}")
        if metadata['author_name'] == "Autor Desconhecido": # Se ainda não achou
            print("   AVISO: Nome do autor não encontrado.")


    # Extrair slug da história da URL do primeiro capítulo (mais confiável)
    if metadata['first_chapter_url']:
        try:
            # Ex: https://www.royalroad.com/fiction/12345/some-story/chapter/123456/chapter-one
            # Queremos "some-story"
            parts = metadata['first_chapter_url'].split('/fiction/')
            if len(parts) > 1:
                slug_part = parts[1].split('/')
                if len(slug_part) > 1:
                     metadata['story_slug'] = _sanitize_filename(slug_part[1]) # slug_part[0] é o ID da ficção
                     print(f"   Slug da história (da URL do capítulo) encontrado: {metadata['story_slug']}")
        except IndexError:
            pass # Deixa o slug como None se não conseguir extrair

    if not metadata['story_slug']: # Fallback para a URL de overview
        try:
            parts = overview_url.split('/fiction/')
            if len(parts) > 1:
                slug_part = parts[1].split('/')
                if len(slug_part) > 1: # /fiction/ID/slug/...
                    metadata['story_slug'] = _sanitize_filename(slug_part[1])
                    print(f"   Slug da história (da URL de overview) encontrado: {metadata['story_slug']}")
                elif len(slug_part) == 1 and slug_part[0]: # /fiction/ID (se não tiver slug na URL)
                    # Neste caso, o título pode ser uma boa alternativa para o nome da pasta
                    metadata['story_slug'] = _sanitize_filename(metadata['story_title'])
                    print(f"   Slug da história (fallback do título) usado: {metadata['story_slug']}")

        except IndexError:
            print("   AVISO: Não foi possível extrair o slug da história da URL de overview. Usando título.")
            metadata['story_slug'] = _sanitize_filename(metadata['story_title'])

    if not metadata['story_slug'] or metadata['story_slug'] == "título-desconhecido":
        # Último recurso, usar um nome genérico se tudo falhar
        timestamp_slug = f"story_{int(time.time())}"
        print(f"   AVISO: Slug da história não pôde ser determinado, usando slug genérico: {timestamp_slug}")
        metadata['story_slug'] = timestamp_slug


    return metadata


def _download_chapter_html(chapter_url: str) -> requests.Response | None:
    """
    Baixa o conteúdo HTML de uma URL de capítulo.
    Retorna o objeto de resposta da requisição ou None em caso de erro.
    """
    return _download_page_html(chapter_url) # Reutiliza a função genérica

# ... (restante de _parse_chapter_html, _sanitize_filename permanecem os mesmos)
def _parse_chapter_html(html_content: str, current_page_url: str) -> dict:
    """
    Analisa o HTML bruto de um capítulo e extrai título, conteúdo e URL do próximo capítulo.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Título do Capítulo
    # Tentativa 1: Pelo h1 específico no cabeçalho da ficção na página do capítulo
    title_tag_h1_specific = soup.select_one('div.fic-header h1.font-white.break-word, h1.break-word[property="name"]')
    # Tentativa 2: Pelo h1 dentro da div.chapter-content (se o crawler anterior salvou assim)
    title_tag_chapter_content = soup.select_one('div.chapter-content h1')
    # Tentativa 3: Pelo h1 mais proeminente na página do capítulo
    title_tag_general_h1 = soup.find('h1')
    # Tentativa 4: Pela tag <title> da página
    page_title_tag = soup.find('title')

    title = "Título Desconhecido"

    if title_tag_h1_specific:
        title = title_tag_h1_specific.text.strip()
    elif title_tag_chapter_content:
        title = title_tag_chapter_content.text.strip()
    elif title_tag_general_h1:
        title = title_tag_general_h1.text.strip()
    elif page_title_tag:
        # Ex: "Chapter Title - Story Name | Royal Road" ou "Chapter Title | Royal Road"
        title_text = page_title_tag.text.split('|')[0].strip()
        # Remove o nome da história se estiver presente, comum em títulos de página
        # Isso é heurístico e pode precisar de ajuste.
        # Tentaremos remover " - Story Name" se existir.
        # Se o título da história puder ser passado para cá, seria mais robusto.
        parts = title_text.split(' - ')
        if len(parts) > 1 and len(parts[0]) < len(parts[1]): # Heurística: título do cap é menor
            title = parts[0].strip()
        else:
            title = title_text

    # Conteúdo da História
    content_div = soup.find('div', class_='chapter-content')
    if not content_div: # Fallback para algumas estruturas diferentes
        content_div = soup.find('div', class_='prose') # Exemplo de outra classe de conteúdo
    content_html = str(content_div) if content_div else "<p>Conteúdo não encontrado.</p>"

    # Link do Próximo Capítulo
    next_chapter_url = None
    # Prioridade para link rel="next"
    next_link_tag_rel = soup.find('link', rel='next')
    if next_link_tag_rel and next_link_tag_rel.get('href'):
        relative_url = next_link_tag_rel['href']
        next_chapter_url = urljoin(current_page_url, relative_url)
    else:
        # Fallback para botões "Next", "Próximo", etc. (mais abrangente)
        # Seleciona links que contenham "Next" ou "Próximo" no texto, priorizando classes de botão
        next_buttons = soup.select('a.btn[href], a.button[href], a[class*="next" i][href]')
        found_button = False
        for button in next_buttons:
            button_text = button.text.strip().lower()
            if "next" in button_text or "próximo" in button_text or "proximo" in button_text:
                relative_url = button['href']
                if relative_url and relative_url != "#" and "javascript:void(0)" not in relative_url:
                    next_chapter_url = urljoin(current_page_url, relative_url)
                    found_button = True
                    break
        # Se não encontrou com seletor específico, tenta uma busca mais genérica por texto
        if not found_button:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                link_text = link.text.strip().lower()
                if ("next" in link_text or "próximo" in link_text or "proximo" in link_text) and \
                   ("previous" not in link_text and "anterior" not in link_text): # Evitar links de "previous"
                    relative_url = link['href']
                    if relative_url and relative_url != "#" and "javascript:void(0)" not in relative_url:
                        # Verificação adicional para evitar links que não são de capítulo
                        # (ex: /comment/next, /forum/next)
                        if '/chapter/' in relative_url or '/fiction/' in relative_url or re.match(r'.*/\d+/?$', relative_url):
                             next_chapter_url = urljoin(current_page_url, relative_url)
                             break


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
    # Remove pontos no início ou fim, e múltiplos pontos
    sanitized = re.sub(r'^\.|\.$', '', sanitized)
    sanitized = re.sub(r'\.{2,}', '.', sanitized)
    # Limita o comprimento para evitar nomes de arquivo excessivamente longos
    return sanitized[:100] # Mantém os primeiros 100 caracteres


def download_story(first_chapter_url: str, output_folder: str, story_slug_override: str = None):
    """
    Baixa todos os capítulos de uma história da Royal Road, começando pela URL do primeiro capítulo.
    """
    story_output_folder = output_folder # Por padrão, salva diretamente na pasta de output fornecida
                                        # que já deve ser a pasta específica da história.

    if story_slug_override:
        story_specific_folder_name = _sanitize_filename(story_slug_override)
    else:
        # Tenta extrair o slug da URL se não foi fornecido
        try:
            story_specific_folder_name = first_chapter_url.split('/fiction/')[1].split('/')[1]
            story_specific_folder_name = _sanitize_filename(story_specific_folder_name)
        except IndexError:
            # Se não conseguir extrair, usa um nome genérico baseado no tempo para a subpasta
            story_specific_folder_name = f"story_{int(time.time())}"
            print(f"Não foi possível extrair o nome da história da URL, usando slug genérico para a pasta: {story_specific_folder_name}")

    # A pasta 'output_folder' passada para download_story já deve ser a base
    # onde a pasta da história (story_specific_folder_name) será criada ou usada.
    # Ex: output_folder = "downloaded_stories"
    #     story_output_folder_final = "downloaded_stories/my-story-slug"

    story_output_folder_final = os.path.join(output_folder, story_specific_folder_name)

    if not os.path.exists(story_output_folder_final):
        print(f"Criando pasta de saída para capítulos: {story_output_folder_final}")
        os.makedirs(story_output_folder_final, exist_ok=True)
    else:
        print(f"Usando pasta de saída existente para capítulos: {story_output_folder_final}")


    current_chapter_url = first_chapter_url
    chapter_number = 1

    while current_chapter_url:
        print(f"\nBaixando capítulo {chapter_number}...")

        response = _download_chapter_html(current_chapter_url)
        if not response:
            print(f"Falha ao baixar o capítulo {chapter_number} de {current_chapter_url}.")
            # Decidir se deve parar ou tentar pular. Por enquanto, paramos.
            break

        # Adiciona uma verificação simples para ter certeza que o conteúdo é HTML
        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' not in content_type:
            print(f"   AVISO: Conteúdo baixado de {current_chapter_url} não parece ser HTML (Content-Type: {content_type}). Tentando processar de qualquer maneira.")
            # Pode ser um erro ou um arquivo (ex: imagem) vinculado como próximo capítulo.
            # Se for um erro comum (ex: página não encontrada que não retornou 404),
            # o parse_chapter_html pode falhar graciosamente.

        chapter_data = _parse_chapter_html(response.text, current_chapter_url)

        title = chapter_data['title']
        content_html = chapter_data['content_html']
        next_url = chapter_data['next_chapter_url']

        # Se o título for "Título Desconhecido" e o número do capítulo for 1,
        # tenta usar o nome do slug da história como um título mais descritivo.
        if title == "Título Desconhecido" and chapter_number == 1 and story_slug_override:
            title = story_slug_override.replace('-', ' ').title() + " - Capítulo 1"


        print(f"   Título do Capítulo: {title}")
        if not next_url:
            print("   Link do próximo capítulo não encontrado nesta página.")


        # Sanitizar o título para usar como parte do nome do arquivo
        safe_title = _sanitize_filename(title if title else f"capitulo_{chapter_number:03d}")
        # Garante que o nome do arquivo não seja excessivamente longo e tenha um número.
        filename_base = f"capitulo_{chapter_number:03d}_{safe_title}"
        filename = f"{filename_base[:150]}.html" # Limita o nome do arquivo total também

        filepath = os.path.join(story_output_folder_final, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                # Escreve uma estrutura HTML básica para o capítulo
                f.write("<!DOCTYPE html>\n<html lang=\"pt-BR\">\n<head>\n")
                f.write(f"  <meta charset=\"UTF-8\">\n  <title>{title if title else 'Capítulo ' + str(chapter_number)}</title>\n")
                # Adiciona um CSS simples para melhor legibilidade se aberto diretamente
                f.write("  <style>\n")
                f.write("    body { font-family: sans-serif; margin: 20px; line-height: 1.6; }\n")
                f.write("    .chapter-content { max-width: 800px; margin: 0 auto; padding: 1em; }\n")
                f.write("    h1 { font-size: 1.8em; margin-bottom: 1em; }\n")
                f.write("    p { margin-bottom: 1em; }\n")
                f.write("  </style>\n")
                f.write("</head>\n<body>\n")
                f.write(f"<h1>{title if title else 'Chapter ' + str(chapter_number)}</h1>\n")
                f.write(content_html) # content_html já é uma string HTML
                f.write("\n</body>\n</html>")
            print(f"   Salvo em: {filepath}")
        except IOError as e:
            print(f"   ERRO ao salvar o arquivo {filepath}: {e}")
            # Decide se quer parar ou continuar para o próximo capítulo
            # Por enquanto, vamos continuar
        except Exception as ex:
            print(f"   ERRO inesperado ao salvar o arquivo {filepath}: {ex}")


        current_chapter_url = next_url

        if not current_chapter_url:
            print("\nFim da história alcançado (próximo capítulo não encontrado ou URL inválida).")
            break

        # Verifica se a URL do próximo capítulo é a mesma da atual para evitar loops infinitos
        if current_chapter_url == response.url:
            print(f"\nAVISO: URL do próximo capítulo ({current_chapter_url}) é a mesma da página atual. Interrompendo para evitar loop.")
            break

        chapter_number += 1

        # Atraso para não sobrecarregar o servidor
        delay = random.uniform(1.5, 3.5) # segundos, randomizado
        print(f"   Aguardando {delay:.1f} segundos antes do próximo capítulo...")
        time.sleep(delay)

    print("\nProcesso de download de capítulos concluído.")
    return story_output_folder_final # Retorna o caminho da pasta onde os capítulos foram salvos


if __name__ == '__main__':
    # Teste rápido para fetch_story_metadata_and_first_chapter
    test_overview_url = "https://www.royalroad.com/fiction/115305/pioneer-of-the-abyss-an-underwater-livestreamed" # URL de exemplo do usuário
    # test_overview_url = "https://www.royalroad.com/fiction/76844/the-final-wish-a-litrpg-adventure" # Outro exemplo
    print(f"Iniciando teste de busca de metadados para: {test_overview_url}")
    metadata = fetch_story_metadata_and_first_chapter(test_overview_url)
    if metadata:
        print("\nMetadados encontrados:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")

        # Teste rápido para download_story (opcional, geralmente isso iria no main.py)
        if metadata.get('first_chapter_url') and metadata.get('story_slug'):
            test_output_base_folder = "downloaded_story_test_from_overview"
            if not os.path.exists(test_output_base_folder):
                os.makedirs(test_output_base_folder, exist_ok=True)

            print(f"\nIniciando teste de download para: {metadata['first_chapter_url']}")
            # Passa o test_output_base_folder, e download_story criará a subpasta do slug dentro dele.
            downloaded_to = download_story(metadata['first_chapter_url'], test_output_base_folder, story_slug_override=metadata['story_slug'])
            print(f"Download de teste concluído. Capítulos em: {downloaded_to}")
        else:
            print("\nNão foi possível testar o download, metadados incompletos (URL do primeiro capítulo ou slug faltando).")

    else:
        print("\nTeste de busca de metadados falhou.")