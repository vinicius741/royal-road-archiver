# main.py
import typer
import os
# Importe a função de download do seu módulo crawler
from core.crawler import download_story

# Mantenha no_args_is_help=True, é uma boa prática.
# O dummy command 'test' também pode ser mantido para garantir o comportamento de subcomandos.
app = typer.Typer(help="CLI para baixar histórias da Royal Road.", no_args_is_help=True)

@app.command(name="crawl") # Nome explícito para o comando
def crawl_story_command(
    first_chapter_url: str = typer.Argument(..., help="A URL completa do primeiro capítulo da história."),
    output_folder: str = typer.Option(
        "downloaded_stories",
        "--out",
        "-o",
        help="Pasta base onde os capítulos da história serão salvos (uma subpasta com o nome da história será criada aqui)."
    )
):
    """
    Baixa uma história da Royal Road capítulo por capítulo.
    """
    typer.echo(f"Iniciando download da história a partir de: {first_chapter_url}")

    # Garante que o caminho do output_folder seja absoluto
    # ou relativo ao diretório atual de forma consistente.
    abs_output_folder = os.path.abspath(output_folder)

    # Cria a pasta de saída base se não existir
    if not os.path.exists(abs_output_folder):
        try:
            os.makedirs(abs_output_folder, exist_ok=True)
            typer.echo(f"Pasta de saída base criada: {abs_output_folder}")
        except OSError as e:
            typer.secho(f"Erro ao criar pasta de saída base '{abs_output_folder}': {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
    else:
        typer.echo(f"Usando pasta de saída base existente: {abs_output_folder}")

    try:
        # Chama a função de download real
        download_story(first_chapter_url, abs_output_folder)
        typer.secho("\nDownload da história concluído com sucesso!", fg=typer.colors.GREEN)
    except ImportError:
         typer.secho("Erro Crítico: Não foi possível importar 'download_story' de 'core.crawler'. Verifique o arquivo e a estrutura do projeto.", fg=typer.colors.RED)
         raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"\nOcorreu um erro durante o download: {e}", fg=typer.colors.RED)
        # Para depuração, você pode querer imprimir o traceback completo:
        import traceback
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

# Você pode manter este comando de teste se quiser, ou removê-lo.
# Ele ajudou a resolver o problema e não prejudica se ficar.
@app.command()
def test():
    """
    Um comando de teste para verificar a configuração do Typer.
    """
    typer.echo("Comando de teste 'test' executado com sucesso!")

if __name__ == "__main__":
    app()