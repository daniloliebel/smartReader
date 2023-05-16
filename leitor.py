from PyPDF2 import PdfReader
import os
import re
import json
import streamlit as st
from io import StringIO
import pandas as pd
import requests
from taxasB3 import taxas

st.set_page_config(layout="wide")

#pasta = 'arquivos'
def extrairTextoAbaixo(linhas, regexBusca, regexValor, posicaoValor):

    for line_num in range(len(linhas)):
        match = re.search(regexBusca, linhas[line_num])

        if match:
            matches = re.findall(regexValor, linhas[line_num + 1])
            if len(matches) > 0 and len(matches) >= posicaoValor:
                valor = matches[posicaoValor].strip()
                if valor.isnumeric():
                    valor = int(valor)
                elif valor.replace(',', '').isnumeric():
                    valor = float(valor.replace('.', '').replace(',', '.'))
                return valor
            else:
                return ''

def extrairValorLinha(linha, regexValor):
    valor = re.findall(regexValor, linha)[0]
    return valor
            
def extrairTabelaMercadorias(linhas, inicioTabela, fimTabela):
    linhasTabela = []
    for line_num in range(len(linhas)):
        matchInicio = re.search(inicioTabela, linhas[line_num])
        if matchInicio:
            linhaInicio = line_num
        matchFinal = re.search(fimTabela, linhas[line_num])
        if matchFinal:
            linhaFinal = line_num
    for linha in range(linhaInicio +1, linhaFinal):
        linhasTabela.append(linhas[linha])
    return linhasTabela

def processarPdfGenial(nomeArquivo, reader):
    pdf_text = ''
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        pdf_text += page.extract_text()

    # dividir o texto em uma lista de linhas
    lines = pdf_text.splitlines()
    cnpjCorretora = extrairTextoAbaixo(lines, r'^C.N.P.J. Corretora', r'(\d{2}\.\d{3}\.\d{3}\/\d{4}\-\d{2}$)', 0).strip()
    if cnpjCorretora != '27.652.684/0001-62':
        retornoErro = {
            "Mensagem": "O arquivo PDF deve ser da corretora Genial"
        }
        return retornoErro
    tabela = extrairTabelaMercadorias(lines, r'^C/V Mercadoria', r'Venda disponível')
    tabelaArray = []
    for linhaTabela in tabela:
        cv = extrairValorLinha(linhaTabela, r'([a-zA-Z])')
        linhaTabela = linhaTabela[len(cv):].strip()
        mercadoria = extrairValorLinha(linhaTabela, r'([\w\d ]+)\d{2}\/\d{2}\/\d{4}')
        linhaTabela = linhaTabela[len(mercadoria):].strip()
        vencimento = extrairValorLinha(linhaTabela, r'(\d{2}\/\d{2}\/\d{4})')
        linhaTabela = linhaTabela[len(vencimento):].strip()
        quantidade = extrairValorLinha(linhaTabela, r'([\d]+)')
        linhaTabela = linhaTabela[len(quantidade):].strip()
        precoAjuste = extrairValorLinha(linhaTabela, r'([\d.,]+)')
        linhaTabela = linhaTabela[len(precoAjuste):].strip()
        tipoNegocio = extrairValorLinha(linhaTabela, r'(DAY TRADE)')
        linhaTabela = linhaTabela[len(tipoNegocio):].strip()
        valorOperacao = extrairValorLinha(linhaTabela, r'(\d{1,},\d{1,})')
        linhaTabela = linhaTabela[len(valorOperacao):].strip()
        dc = extrairValorLinha(linhaTabela, r'([a-zA-Z])')
        linhaTabela = linhaTabela[len(dc):].strip()
        taxaOperacional = extrairValorLinha(linhaTabela, r'(\d{1,},\d{1,})')
        linhaJson = {
            "cv": cv,
            "mercadoria": mercadoria.strip(),
            "vencimento": vencimento.strip(),
            "quantidade": int(quantidade.strip()),
            "precoAjuste": float(precoAjuste.strip().replace('.', '').replace(',', '.')),
            "tipoNegocio": tipoNegocio.strip(),
            "valorOperacao": float(valorOperacao.strip().replace('.', '').replace(',', '.')),
            "dc": dc.strip(),
            "taxaOperacional": float(taxaOperacional.strip().replace('.', '').replace(',', '.'))
        }
        #print(linhaJson)
        tabelaArray.append(linhaJson)


    irrf = extrairTextoAbaixo(lines, r'^IRRF', r'(\d{1,},\d{1,})', 1)
    #print(irrf)
    valorNegocios = extrairTextoAbaixo(lines, r'^Venda disponível', r'(\d{1,},\d{1,})', 0)
    #print(valorNegocios)
    taxasBMF = extrairTextoAbaixo(lines, r'^IRRF', r'(\d{1,},\d{1,})', 4)
    #print(taxasBMF)
    totalDespesas = extrairTextoAbaixo(lines, r'^\+ Outros', r'(\d{1,},\d{1,})', 3)
    #print(totalDespesas)
    totalLiquido = extrairTextoAbaixo(lines, r'^Outros IRRF', r'(\d{1,},\d{1,})', 3)
    #print(totalLiquido)
    cnpjCorretora = extrairTextoAbaixo(lines, r'^C.N.P.J. Corretora', r'(\d{2}\.\d{3}\.\d{3}\/\d{4}\-\d{2}$)', 0)
    #print(cnpjCorretora)
    numeroCorretora = extrairTextoAbaixo(lines, r'Número da corretora$', r'(\d{1,}.*)', 0)
    #print(numeroCorretora)
    numeroNota = extrairTextoAbaixo(lines, r'^Data pregão', r'(\d{1,})$', 0)
    #print(numeroNota)
    nomeCliente = extrairTextoAbaixo(lines, r'^Cliente C.N.P.J.', r'([A-Za-záàâãéèêíïóôõöúçñÁÀÂÃÉÈÍÏÓÔÕÖÚÇÑ ]+)', 0)
    #print(nomeCliente)
    cpfCnpjCliente = extrairTextoAbaixo(lines, r'^Cliente C.N.P.J.', r'(^\d{3}\.\d{3}\.\d{3}\-\d{2}|^\d{2}\.\d{3}\.\d{3}\/\d{4}\-\d{2})', 0)
    #print(cpfCnpjCliente)
    codigoCliente = extrairTextoAbaixo(lines, r'Código do cliente', r'(^\d{1,})', 0)
    #print(codigoCliente)
    assessor = extrairTextoAbaixo(lines, r'Código do cliente', r'(\d{1,})', 1)
    #print(assessor)
    dataPregao = extrairTextoAbaixo(lines, r'Data pregão', r'(\d{2}\/\d{2}\/\d{4})', 0)
    #print(dataPregao)

    #get taxas B3 data pregao
    taxa = taxas(dataPregao)

    infosNota = {"principal" : {
        "cnpjCorretora": cnpjCorretora,
        "numeroCorretora": numeroCorretora,
        "numeroNota": numeroNota,
        "nomeCliente": nomeCliente,
        "cpfCnpjCliente": cpfCnpjCliente,
        "codigoCliente": codigoCliente,
        "assessor": assessor,
        "dataPregao": dataPregao,
        "irrf": irrf,
        "valorNegocios": valorNegocios,
        "taxasBMF": taxasBMF,
        "totalDespesas": totalDespesas,
        "totalLiquido": totalLiquido,
        "taxaB3": float(taxa)
    },
    "tabelaValores": tabelaArray
    }
    #print(infosNota)
    #print(infosNota.get('valorNegocios'))
    #print(infosNota.get('irrf') + infosNota.get('valorNegocios'))
    totalValorOperacao = 0        

    #print(totalValorOperacao)
    return infosNota

# Itera sobre a lista de arquivos
uploaded_files = st.file_uploader("Escolha o(s) PDF a ser(em) processado(s)", type=['pdf'], accept_multiple_files=True)
tabelaValTotalNotas = []
tabelaPrinTotalNotas = []
notaProcessada = []
if uploaded_files:
    for file in uploaded_files:
        reader = PdfReader(file)
        pdfProcessado = processarPdfGenial(file.name, reader)
        dfPrincipal = pd.json_normalize(pdfProcessado.get('principal'))
        st.text(file.name)
        dfPrincipal['irrf'] = dfPrincipal['irrf'].map('R${:,.2f}'.format)
        dfPrincipal['valorNegocios'] = dfPrincipal['valorNegocios'].map('R${:,.2f}'.format)
        dfPrincipal['taxasBMF'] = dfPrincipal['taxasBMF'].map('R${:,.2f}'.format)
        dfPrincipal['totalDespesas'] = dfPrincipal['totalDespesas'].map('R${:,.2f}'.format)
        dfPrincipal['totalLiquido'] = dfPrincipal['totalLiquido'].map('R${:,.2f}'.format)
        st.dataframe(dfPrincipal)
        dfTabela = pd.json_normalize(pdfProcessado.get('tabelaValores'))
        dfTabela['precoAjuste'] = dfTabela['precoAjuste'].map('R${:,.2f}'.format)
        dfTabela['valorOperacao'] = dfTabela['valorOperacao'].map('R${:,.2f}'.format)
        st.dataframe(dfTabela)
        tabelaPrinTotalNotas.append(pdfProcessado.get('principal'))
        if not tabelaValTotalNotas:
            tabelaValTotalNotas = pdfProcessado.get('tabelaValores').copy()
        else:
            tabelaValTotalNotas = tabelaValTotalNotas + pdfProcessado.get('tabelaValores')
        notaProcessada.append(pdfProcessado)
    totalIrrf = 0
    totalDespesas = 0
    totalTaxasBMF = 0
    totalLiquido = 0
    datasNotas = []
    for data in notaProcessada:
        dt = data.get('principal').get('dataPregao')
        if dt not in datasNotas:
            datasNotas.append(dt)
    #print(datasNotas)
    resultadoNotaPorData = []
    for data in datasNotas:
        notasPorData = filter(lambda x: x.get('principal').get("dataPregao") == data, notaProcessada)
        totalIrrf = 0
        totalDespesas = 0
        totalTaxasBMF = 0
        totalLiquido = 0
        for notaData in notasPorData:
            totalIrrf += notaData.get('principal').get('irrf')
            totalDespesas += notaData.get('principal').get('totalDespesas')
            totalTaxasBMF += notaData.get('principal').get('taxasBMF')
            totalLiquido += notaData.get('principal').get('totalLiquido')
            totalValorOperacaoWIN = 0
            totalQuantidadeWIN = 0
            totalValorOperacaoWDO = 0
            totalQuantidadeWDO = 0
            for valor in notaData.get('tabelaValores'):
                if valor.get('dc') == 'D' and 'WIN' in valor.get('mercadoria'):
                    totalValorOperacaoWIN -= valor.get('valorOperacao')
                if valor.get('dc') == 'C' and 'WIN' in valor.get('mercadoria'):
                    totalValorOperacaoWIN += valor.get('valorOperacao')

                if valor.get('dc') == 'D' and 'WDO' in valor.get('mercadoria'):
                    totalValorOperacaoWDO -= valor.get('valorOperacao')
                if valor.get('dc') == 'C' and 'WDO' in valor.get('mercadoria'):
                    totalValorOperacaoWDO += valor.get('valorOperacao')
        
                if 'WIN' in valor.get('mercadoria'):
                    totalQuantidadeWIN += valor.get('quantidade')

                if 'WDO' in valor.get('mercadoria'):
                    totalQuantidadeWDO += valor.get('quantidade')
            taxasWIN = totalQuantidadeWIN * notaData.get('principal').get('taxaB3')
            irrfWIN = (totalValorOperacaoWIN - taxasWIN) * 0.01
            taxasWDO = totalDespesas - taxasWIN
            irrfWDO = totalIrrf - irrfWIN

            resultadoValorWIN = totalValorOperacaoWIN - taxasWIN
            resultadoIrrfWIN = irrfWIN

            resultadoValorWDO = totalValorOperacaoWDO - taxasWDO
            resultadoIrrfWDO = irrfWDO
        resultadoNotaPorData.append({"data": data, 
                                     "totalIrrf": totalIrrf,
                                     "totalDespesas": totalDespesas,
                                     "totalTaxasBMF": totalTaxasBMF,
                                     "totalLiquido": totalLiquido,
                                     "ValorWIN": resultadoValorWIN,
                                     "IrrfWIN": resultadoIrrfWIN,
                                     "ValorWDO": resultadoValorWDO,
                                     "IrrfWDO": resultadoIrrfWDO 
                                    })
    print(resultadoNotaPorData)
    dfTotais = pd.DataFrame(resultadoNotaPorData)

    print(dfTotais['ValorWIN'])
    dfTotais['ValorWIN'] = dfTotais['ValorWIN'].map('R$ {:,.2f}'.format)
    dfTotais['IrrfWIN'] = dfTotais['IrrfWIN'].map('R$ {:,.2f}'.format)
    dfTotais['ValorWDO'] = dfTotais['ValorWDO'].map('R$ {:,.2f}'.format)
    dfTotais['IrrfWDO'] = dfTotais['IrrfWDO'].map('R$ {:,.2f}'.format)
    st.subheader('Resultado total das notas')
    st.dataframe(dfTotais)