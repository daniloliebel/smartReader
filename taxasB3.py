import requests
from bs4 import BeautifulSoup

#dataPregao = '05/05/2023'
def taxas(dataPregao):
    print(dataPregao)
    headers = {}
    cookies = {}
    request1 = requests.get("https://www.bmf.com.br/bmfbovespa/pages/boletim1/custos/carregaCombo.asp?idioma=1&tipo=ConsultarTamanhoContrato&mercado=2&mercadoria=WIN&dataPregao=" + dataPregao.replace('/', ''))
    headers.update(request1.headers)
    cookies.update(request1.cookies.get_dict())
    request2 = requests.post("https://www.bmf.com.br/bmfbovespa/pages/boletim1/custos/carregaCombo.asp?idioma=1&tipo=ConsultarTarifas&mercado=2&mercadoria=WIN&dataPregao=" + dataPregao.replace('/', ''))
    headers.update(request2.headers)
    cookies.update(request2.cookies.get_dict())
    requestFinal = requests.get("https://www.bmf.com.br/bmfbovespa/pages/boletim1/custos/lum-tarifacao-custos-modalidade.asp", headers=headers, cookies=cookies)
    soup = BeautifulSoup(requestFinal.text, 'html.parser')
    tabelaTaxas = soup.find('table', {'id': 'dados1'})
    linhas = tabelaTaxas.find_all('tr')
    for linha in linhas:
        celulas = linha.find_all('td')
        if len(celulas):
            taxa1 = celulas[2].text.replace('.','').replace(',','.')
            taxa2 = celulas[7].text.replace('.','').replace(',','.')
            break
    return float(taxa1) + float(taxa2)
    #print(requestFinal.text)