param(
    [string]$HtmlPath = (Join-Path $PSScriptRoot "Documentacao_Projeto_Metas_Levo.html"),
    [string]$OutputPath = (Join-Path $PSScriptRoot "Documentacao_Projeto_Metas_Levo.docx")
)

$ErrorActionPreference = "Stop"

$html = (Resolve-Path $HtmlPath).Path
$output = [System.IO.Path]::GetFullPath($OutputPath)
$word = $null
$document = $null

try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0

    # O Word converte o HTML para o formato nativo, incorporando estilos, tabelas e a marca.
    $document = $word.Documents.Open($html, $false, $false)

    # Troca a imagem vinculada do HTML por uma copia realmente incorporada no DOCX.
    $logoPath = [System.IO.Path]::GetFullPath(
        (Join-Path $PSScriptRoot "..\Bello Alimentos 02.png")
    )
    if ($document.InlineShapes.Count -gt 0) {
        $logoRange = $document.InlineShapes.Item(1).Range.Duplicate
        $document.InlineShapes.Item(1).Delete()
    } else {
        $logoRange = $document.Range(0, 0)
    }
    $embeddedLogo = $document.InlineShapes.AddPicture($logoPath, $false, $true, $logoRange)
    $embeddedLogo.LockAspectRatio = -1
    $embeddedLogo.Width = 195
    $embeddedLogo.Range.ParagraphFormat.Alignment = 1

    # Substitui o marcador por um sumario automatico baseado nos titulos de niveis 1 a 3.
    $tocRange = $document.Content.Duplicate
    $find = $tocRange.Find
    $find.ClearFormatting()
    $find.Text = "[[TOC]]"
    if ($find.Execute()) {
        $tocRange.Text = ""
        [void]$document.TablesOfContents.Add($tocRange, $true, 1, 3)
    }

    # Cabecalho e rodape profissionais; a capa permanece limpa.
    foreach ($section in $document.Sections) {
        $section.PageSetup.DifferentFirstPageHeaderFooter = -1

        $header = $section.Headers.Item(1).Range
        $header.Text = "METAS LEVO  |  DOCUMENTACAO DE PROJETO E DOSSIE TECNICO"
        $header.Font.Name = "Aptos"
        $header.Font.Size = 8
        $header.Font.Color = 6114592
        $header.ParagraphFormat.Alignment = 2

        $footer = $section.Footers.Item(1).Range
        $footer.Text = "Uso interno  |  Versao 1.0  |  16/07/2026  |  Pagina "
        $footer.Font.Name = "Aptos"
        $footer.Font.Size = 8
        $footer.Font.Color = 6114592
        $footer.ParagraphFormat.Alignment = 1
        $footer.Collapse(0)
        [void]$footer.Fields.Add($footer, -1, "PAGE", $true)
        $footer.Collapse(0)
        $footer.InsertAfter(" de ")
        $footer.Collapse(0)
        [void]$footer.Fields.Add($footer, -1, "NUMPAGES", $true)
    }

    # Propriedades uteis para pesquisa e governanca documental.
    try {
        $document.BuiltInDocumentProperties.Item("Title").Value =
            "Metas Levo - Documentacao de Projeto e Dossie Tecnico"
        $document.BuiltInDocumentProperties.Item("Subject").Value =
            "Negocio, requisitos, arquitetura, infraestrutura, dados, seguranca e oportunidades de IA"
        $document.BuiltInDocumentProperties.Item("Company").Value = "Levo Alimentos LTDA"
        $document.BuiltInDocumentProperties.Item("Comments").Value =
            "Documento gerado a partir do estado observado do projeto em 16/07/2026."
    } catch {
        # Algumas instalacoes do Office nao expoem todas as propriedades; isso nao invalida o arquivo.
    }

    foreach ($field in $document.Fields) {
        [void]$field.Update()
    }
    foreach ($toc in $document.TablesOfContents) {
        [void]$toc.Update()
    }

    # 12 = wdFormatXMLDocument (.docx).
    $document.SaveAs2($output, 12)

    $pages = $document.ComputeStatistics(2)
    $words = $document.ComputeStatistics(0)
    $tables = $document.Tables.Count

    $document.Close($false)
    $document = $null
    $word.Quit()
    $word = $null

    $file = Get-Item -LiteralPath $output
    [PSCustomObject]@{
        Arquivo = $file.FullName
        TamanhoBytes = $file.Length
        Paginas = $pages
        Palavras = $words
        Tabelas = $tables
    } | Format-List
}
finally {
    if ($document -ne $null) {
        try { $document.Close($false) } catch {}
    }
    if ($word -ne $null) {
        try { $word.Quit() } catch {}
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
