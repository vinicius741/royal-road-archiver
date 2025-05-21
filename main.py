import re
import typer
import os
import traceback
# Adicionar import para a nova função no crawler
from core.crawler import download_story, fetch_story_metadata_and_first_chapter
from core.processor import process_story_chapters
from core.epub_builder import build_epubs_for_story

app = typer.Typer(help="CLI for downloading and processing stories from Royal Road.", no_args_is_help=True)

def is_overview_url(url: str) -> bool:
    """Verifica se a URL é provavelmente uma página de visão geral (não contém /chapter/)."""
    return "/chapter/" not in url and "/fiction/" in url

@app.command(name="crawl")
def crawl_story_command(
    story_url: str = typer.Argument(..., help="The full URL of the story's overview page OR the first chapter."),
    output_folder: str = typer.Option(
        "downloaded_stories",
        "--out",
        "-o",
        help="Base folder where the raw HTML chapters of the story will be saved (a subfolder with the story name will be created here)."
    )
):
    """
    Downloads a story from Royal Road chapter by chapter as raw HTML files.
    Can start from a story overview page or a direct first chapter URL.
    """
    typer.echo(f"Iniciando download para URL: {story_url}")
    abs_output_folder = os.path.abspath(output_folder)

    if not os.path.exists(abs_output_folder):
        try:
            os.makedirs(abs_output_folder, exist_ok=True)
            typer.echo(f"Pasta base de saída para downloads criada/confirmada: {abs_output_folder}")
        except OSError as e:
            typer.secho(f"Erro ao criar pasta base de saída '{abs_output_folder}': {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
    else:
        typer.echo(f"Usando pasta base de saída existente para downloads: {abs_output_folder}")

    first_chapter_to_crawl = story_url
    story_slug_for_folder = None

    if is_overview_url(story_url):
        typer.echo("URL detectada como página de visão geral. Buscando metadados...")
        metadata = fetch_story_metadata_and_first_chapter(story_url)
        if not metadata or not metadata.get('first_chapter_url'):
            typer.secho("Falha ao obter metadados ou URL do primeiro capítulo da página de visão geral.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        first_chapter_to_crawl = metadata['first_chapter_url']
        story_slug_for_folder = metadata.get('story_slug') # Usará o slug para nomear a pasta
        typer.echo(f"Primeiro capítulo encontrado: {first_chapter_to_crawl}")
        if story_slug_for_folder:
            typer.echo(f"Slug da história para nome da pasta: {story_slug_for_folder}")
    else:
        typer.echo("URL detectada como página de capítulo.")
        # Tenta extrair o slug da URL do capítulo para nome da pasta
        try:
            story_slug_for_folder = story_url.split('/fiction/')[1].split('/')[1]
            story_slug_for_folder = re.sub(r'[\\/*?:"<>|]', "", story_slug_for_folder)
            story_slug_for_folder = re.sub(r'\s+', '_', story_slug_for_folder)[:100]
            typer.echo(f"Slug inferido da URL do capítulo: {story_slug_for_folder}")
        except IndexError:
            typer.echo("Não foi possível inferir o slug da URL do capítulo. O nome da pasta pode ser genérico.")


    try:
        # download_story agora espera a pasta base (abs_output_folder) e o slug_override
        # Ele criará abs_output_folder/story_slug_for_folder
        downloaded_story_path = download_story(first_chapter_to_crawl, abs_output_folder, story_slug_override=story_slug_for_folder)
        if downloaded_story_path:
            typer.secho(f"\nDownload dos arquivos HTML brutos concluído com sucesso em: {downloaded_story_path}", fg=typer.colors.GREEN)
        else:
            typer.secho("\nDownload parece ter falhado ou não retornou um caminho.", fg=typer.colors.RED)
            raise typer.Exit(code=1)

    except ImportError:
         typer.secho("Erro Crítico: Não foi possível importar 'download_story' ou 'fetch_story_metadata_and_first_chapter' de 'core.crawler'. Verifique o arquivo e a estrutura do projeto.", fg=typer.colors.RED)
         raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"\nOcorreu um erro durante o download: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

# ... (comando process inalterado)
@app.command(name="process")
def process_story_command(
    input_story_folder: str = typer.Argument(..., help="Path to the folder containing the raw HTML chapters of a single story (e.g., downloaded_stories/story-slug)."),
    output_base_folder: str = typer.Option(
        "processed_stories",
        "--out",
        "-o",
        help="Base folder where the cleaned HTML chapters will be saved (a subfolder with the story name will be created here)."
    )
):
    """
    Processes raw HTML chapters of a story: cleans HTML, removes unwanted tags,
    and saves the processed chapters.
    """
    typer.echo(f"Initiating processing for story files in: {input_story_folder}")

    abs_input_story_folder = os.path.abspath(input_story_folder)
    abs_output_base_folder = os.path.abspath(output_base_folder)

    if not os.path.isdir(abs_input_story_folder):
        typer.secho(f"Error: Input story folder '{abs_input_story_folder}' not found or is not a directory.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # O nome da subpasta em processed_stories será o mesmo que em downloaded_stories
    story_slug_for_processed = os.path.basename(abs_input_story_folder)
    specific_output_folder = os.path.join(abs_output_base_folder, story_slug_for_processed)


    if not os.path.exists(specific_output_folder):
        try:
            os.makedirs(specific_output_folder, exist_ok=True)
            typer.echo(f"Base output folder for processed files created: {specific_output_folder}")
        except OSError as e:
            typer.secho(f"Error creating specific output folder for processed files '{specific_output_folder}': {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
    else:
        typer.echo(f"Using existing specific output folder for processed files: {specific_output_folder}")

    try:
        # Passa a pasta específica onde os capítulos processados da história devem ir
        process_story_chapters(abs_input_story_folder, specific_output_folder)
        typer.secho(f"\nProcessing of story chapters concluded successfully! Output in: {specific_output_folder}", fg=typer.colors.GREEN)
        return specific_output_folder # Retorna o caminho para uso no full-process
    except ImportError:
         typer.secho("Critical Error: Could not import 'process_story_chapters' from 'core.processor'. Check file and project structure.", fg=typer.colors.RED)
         raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"\nAn error occurred during processing: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc()) # For more detailed error
        raise typer.Exit(code=1)


# ... (comando build-epub inalterado)
@app.command(name="build-epub")
def build_epub_command(
    input_processed_folder: str = typer.Argument(..., help="Path to the folder containing the CLEANED HTML chapters of a single story (e.g., processed_stories/story-slug)."),
    output_epub_folder: str = typer.Option(
        "epubs",
        "--out",
        "-o",
        help="Base folder where the generated EPUB files will be saved."
    ),
    chapters_per_epub: int = typer.Option(
        50,
        "--chapters-per-epub",
        "-c",
        min=0, # 0 para um único EPUB com todos os capítulos
        help="Number of chapters to include in each EPUB file. Set to 0 for a single EPUB."
    ),
    author_name: str = typer.Option(
        "Royal Road Archiver",
        "--author",
        "-a",
        help="Author name to be used in the EPUB metadata."
    ),
    story_title: str = typer.Option(
        "Archived Royal Road Story",
        "--title",
        "-t",
        help="Story title to be used in the EPUB metadata. If not provided, it will attempt to extract from the first chapter file."
    )
):
    """
    Generates EPUB files from cleaned HTML chapters.
    """
    typer.echo(f"Initiating EPUB generation for story files in: {input_processed_folder}")

    abs_input_processed_folder = os.path.abspath(input_processed_folder)
    abs_output_epub_folder = os.path.abspath(output_epub_folder)

    if not os.path.isdir(abs_input_processed_folder):
        typer.secho(f"Error: Input processed folder '{abs_input_processed_folder}' not found or is not a directory.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if not os.path.exists(abs_output_epub_folder):
        try:
            os.makedirs(abs_output_epub_folder, exist_ok=True)
            typer.echo(f"Base output folder for EPUBs created: {abs_output_epub_folder}")
        except OSError as e:
            typer.secho(f"Error creating base output folder for EPUBs '{abs_output_epub_folder}': {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
    else:
        typer.echo(f"Using existing base output folder for EPUBs: {abs_output_epub_folder}")

    # Se chapters_per_epub for 0, passa um número muito grande para ebooklib fazer um só.
    # A lógica interna de build_epubs_for_story já trata isso se chapters_per_epub for grande.
    effective_chapters_per_epub = chapters_per_epub if chapters_per_epub > 0 else 999999


    try:
        build_epubs_for_story(
            input_folder=abs_input_processed_folder, # Esta é a pasta específica da história processada
            output_folder=abs_output_epub_folder,   # EPUBs são salvos diretamente aqui
            chapters_per_epub=effective_chapters_per_epub,
            author_name=author_name,
            story_title=story_title # O título da história já deve estar correto aqui
        )
        typer.secho(f"\nEPUB generation concluded successfully! Files in {abs_output_epub_folder}", fg=typer.colors.GREEN)
    except ImportError:
         typer.secho("Critical Error: Could not import 'build_epubs_for_story' from 'core.epub_builder'. Check file and project structure.", fg=typer.colors.RED)
         raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"\nAn error occurred during EPUB generation: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

@app.command()
def test():
    """
    A simple test command for Typer setup.
    """
    typer.echo("CLI 'test' command executed successfully!")

@app.command(name="full-process")
def full_process_command(
    story_url: str = typer.Argument(..., help="The full URL of the story's overview page OR the first chapter."),
    chapters_per_epub: int = typer.Option(
        50,
        "--chapters-per-epub",
        "-c",
        min=0,
        help="Number of chapters to include in each EPUB file. Set to 0 for a single EPUB."
    ),
    author_name_param: str = typer.Option(
        None, # Default para None para que possamos saber se foi fornecido
        "--author",
        "-a",
        help="Author name for EPUB metadata. If not provided and fetching from overview, uses that."
    ),
    story_title_param: str = typer.Option(
        None, # Default para None
        "--title",
        "-t",
        help="Story title for EPUB metadata. If not provided and fetching from overview, uses that."
    )
):
    """
    Performs the full sequence: download, process, and build EPUB for a story.
    Can start from a story overview page or a direct first chapter URL.
    """
    download_base_folder = "downloaded_stories"
    processed_base_folder = "processed_stories"
    epub_base_folder = "epubs"

    # Ensure base folders exist
    for folder in [download_base_folder, processed_base_folder, epub_base_folder]:
        abs_folder = os.path.abspath(folder)
        if not os.path.exists(abs_folder):
            try:
                os.makedirs(abs_folder, exist_ok=True)
                typer.echo(f"Pasta base criada/confirmada: {abs_folder}")
            except OSError as e:
                typer.secho(f"Erro ao criar pasta base '{abs_folder}': {e}", fg=typer.colors.RED)
                raise typer.Exit(code=1)
        else:
            typer.echo(f"Usando pasta base existente: {abs_folder}")

    abs_download_base_folder = os.path.abspath(download_base_folder)
    abs_processed_base_folder = os.path.abspath(processed_base_folder)
    abs_epub_base_folder = os.path.abspath(epub_base_folder)

    # Variáveis para armazenar metadados e caminhos
    first_chapter_to_crawl = story_url
    final_story_title = story_title_param
    final_author_name = author_name_param
    story_slug_for_folders = None # Será usado para criar subpastas consistentes

    # --- 0. Fetch metadata if overview URL ---
    if is_overview_url(story_url):
        typer.echo(f"\n--- Etapa 0: Buscando metadados de {story_url} ---")
        metadata = fetch_story_metadata_and_first_chapter(story_url)
        if not metadata or not metadata.get('first_chapter_url'):
            typer.secho("Falha ao obter metadados ou URL do primeiro capítulo. Abortando.", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        first_chapter_to_crawl = metadata['first_chapter_url']
        story_slug_for_folders = metadata.get('story_slug', None)

        if not final_story_title and metadata.get('story_title') != "Título Desconhecido":
            final_story_title = metadata['story_title']
            typer.echo(f"Título da história (da overview): {final_story_title}")
        if not final_author_name and metadata.get('author_name') != "Autor Desconhecido":
            final_author_name = metadata['author_name']
            typer.echo(f"Autor (da overview): {final_author_name}")

        typer.echo(f"URL do primeiro capítulo para download: {first_chapter_to_crawl}")
        if story_slug_for_folders:
             typer.echo(f"Slug da história para pastas: {story_slug_for_folders}")

    else: # É uma URL de capítulo direto
        typer.echo("URL fornecida é de um capítulo direto.")
        # Tenta extrair o slug da URL do capítulo para nome da pasta
        try:
            slug_parts = first_chapter_to_crawl.split('/fiction/')[1].split('/')
            if len(slug_parts) > 1:
                story_slug_for_folders = re.sub(r'[\\/*?:"<>|]', "", slug_parts[1])
                story_slug_for_folders = re.sub(r'\s+', '_', story_slug_for_folders)[:100]
                typer.echo(f"Slug inferido da URL do capítulo para pastas: {story_slug_for_folders}")
        except IndexError:
            typer.echo("Não foi possível inferir o slug da URL do capítulo para nome de pasta.")


    # Se o slug ainda não foi definido (ex: URL de capítulo inválida ou overview falhou em extrair)
    # ou se o título/autor não foram definidos e não foram fornecidos.
    if not story_slug_for_folders:
        # Gera um slug baseado no título se disponível, ou um slug genérico
        if final_story_title and final_story_title != "Archived Royal Road Story":
            story_slug_for_folders = re.sub(r'[\\/*?:"<>|]', "", final_story_title)
            story_slug_for_folders = re.sub(r'\s+', '_', story_slug_for_folders).lower()[:50]
            typer.echo(f"Slug para pastas gerado a partir do título: {story_slug_for_folders}")
        else:
            story_slug_for_folders = f"story_{int(time.time())}" # Fallback muito genérico
            typer.echo(f"AVISO: Usando slug genérico para pastas: {story_slug_for_folders}")


    # Define padrões se ainda não foram preenchidos pelos metadados ou parâmetros
    if not final_story_title:
        # Se o slug foi bem definido e o título não, tenta usar o slug como base para o título
        if story_slug_for_folders and not story_slug_for_folders.startswith("story_"):
             final_story_title = story_slug_for_folders.replace('-', ' ').replace('_', ' ').title()
             typer.echo(f"Título do EPUB (inferido do slug): {final_story_title}")
        else:
            final_story_title = "Archived Royal Road Story" # Padrão do Typer
            typer.echo(f"Título do EPUB (padrão): {final_story_title}")

    if not final_author_name:
        final_author_name = "Royal Road Archiver" # Padrão do Typer
        typer.echo(f"Autor do EPUB (padrão): {final_author_name}")


    # --- 1. Download Step ---
    typer.echo(f"\n--- Etapa 1: Baixando capítulos de {first_chapter_to_crawl} ---")
    typer.echo(f"Capítulos HTML brutos serão salvos em uma subpasta sob: {abs_download_base_folder}")

    story_specific_download_folder = None
    try:
        # download_story criará a subpasta {story_slug_for_folders} dentro de abs_download_base_folder
        story_specific_download_folder = download_story(first_chapter_to_crawl, abs_download_base_folder, story_slug_override=story_slug_for_folders)
        if not story_specific_download_folder or not os.path.isdir(story_specific_download_folder):
            typer.secho("Erro: A pasta de download da história não foi criada ou retornada corretamente.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        typer.secho(f"Download bem-sucedido. Conteúdo salvo em: {story_specific_download_folder}", fg=typer.colors.GREEN)

    except Exception as e:
        typer.secho(f"\nOcorreu um erro durante a etapa de download: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)


    # --- 2. Process Step ---
    typer.echo(f"\n--- Etapa 2: Processando capítulos da história de {story_specific_download_folder} ---")
    # A pasta processada será abs_processed_base_folder/story_slug_for_folders
    story_specific_processed_folder = os.path.join(abs_processed_base_folder, story_slug_for_folders)
    typer.echo(f"Capítulos processados serão salvos em: {story_specific_processed_folder}")

    try:
        # process_story_chapters recebe a pasta de input (download) e a pasta de output específica para a história processada
        process_story_chapters(story_specific_download_folder, story_specific_processed_folder)
        if not os.path.isdir(story_specific_processed_folder):
             typer.secho(f"Erro: Pasta da história processada '{story_specific_processed_folder}' não foi criada como esperado.", fg=typer.colors.RED)
             raise typer.Exit(code=1)
        typer.secho(f"Processamento bem-sucedido. Conteúdo limpo salvo em: {story_specific_processed_folder}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"\nOcorreu um erro durante a etapa de processamento: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

    # --- 3. Build EPUB Step ---
    typer.echo(f"\n--- Etapa 3: Construindo EPUB(s) de {story_specific_processed_folder} ---")
    typer.echo(f"Arquivos EPUB serão salvos em: {abs_epub_base_folder}")

    effective_chapters_per_epub = chapters_per_epub if chapters_per_epub > 0 else 999999

    try:
        build_epubs_for_story(
            input_folder=story_specific_processed_folder, # Pasta específica com HTMLs limpos
            output_folder=abs_epub_base_folder,       # Pasta base para salvar os .epub
            chapters_per_epub=effective_chapters_per_epub,
            author_name=final_author_name,
            story_title=final_story_title
        )
        typer.secho(f"\nGeração de EPUB bem-sucedida. Arquivos salvos em: {abs_epub_base_folder}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"\nOcorreu um erro durante a etapa de construção do EPUB: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

    typer.secho("\n--- Processo completo concluído com sucesso! ---", fg=typer.colors.CYAN)


if __name__ == "__main__":
    # Adicionar para permitir import random no crawler.py se ele estiver lá
    import random
    app()