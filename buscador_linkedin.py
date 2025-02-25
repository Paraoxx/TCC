import requests
from bs4 import BeautifulSoup
import csv
import pandas as pd
from typing import List, Dict
import time
import random
import logging
from fake_useragent import UserAgent
import sqlite3
from datetime import datetime

# Config log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='busca_linkedin.log'
)

class BuscadorCandidatosLinkedIn:
    def __init__(self, email: str, senha: str, proxies: List[str] = None):
        """Inicializa o buscador com credenciais do LinkedIn"""
        self.email = email
        self.senha = senha
        self.proxies = proxies if proxies else []
        self.sessao = requests.Session()
        self.ua = UserAgent()
        self._configurar_sessao()
        self.criar_conexao_db()
        logging.info("Inicializando buscador...")
    
    def criar_conexao_db(self):
        """Cria as tabelas do banco de dados se não existirem"""
        conn = sqlite3.connect('linkedin.db')
        cursor = conn.cursor()
        
        # Tabela canditados do bd
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidatos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            titulo TEXT,
            empresa TEXT,
            localizacao TEXT,
            experiencia TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Tabela experiências do bd
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS experiencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidato_id INTEGER,
            empresa TEXT,
            cargo TEXT,
            periodo TEXT,
            descricao TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidato_id) REFERENCES candidatos (id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def salvar_candidato_db(self, candidato: Dict):
        """Salva um candidato no banco de dados"""
        conn = sqlite3.connect('linkedin.db')
        cursor = conn.cursor()
        
        # Salva o candidato
        cursor.execute('''
        INSERT OR REPLACE INTO candidatos (
            nome, titulo, empresa, localizacao, experiencia, data_atualizacao
        ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            candidato['nome'],
            candidato['titulo'],
            candidato['empresa'],
            candidato['localizacao'],
            candidato['experiencia'],
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _configurar_sessao(self):
        """Configura a sessão com headers realistas"""
        self.sessao.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1'
        })
        logging.info("Headers configurados com sucesso")
    
    def _login(self):
        """Realiza o login no LinkedIn com tratamento de erros e proxies"""
        tentativas = 0
        max_tentativas = 5
        
        while tentativas < max_tentativas:
            try:
                # proxy aleatório disponível
                if self.proxies:
                    proxy = random.choice(self.proxies)
                    self.sessao.proxies = {
                        'http': proxy,
                        'https': proxy
                    }
                    logging.info(f"Usando proxy: {proxy}")
                
                # token de login
                resposta = self.sessao.get("https://www.linkedin.com/login")
                logging.info(f"Status da página de login: {resposta.status_code}")
                
                if resposta.status_code != 200:
                    raise Exception(f"Erro ao acessar página de login. Status: {resposta.status_code}")
                
                soup = BeautifulSoup(resposta.text, 'html.parser')
                token = soup.find('input', {'name': 'loginCsrfParam'})
                if not token:
                    raise Exception("Token de login não encontrado")
                
                # Faz o login
                dados_login = {
                    'session_key': self.email,
                    'session_password': self.senha,
                    'loginCsrfParam': token['value'],
                    'isJsEnabled': 'true',
                    'defaultChallenge': 'true',
                    'pageInstance': ''.join(random.choices('0123456789abcdef', k=16))
                }
                
                resposta_login = self.sessao.post("https://www.linkedin.com/check/login", data=dados_login)
                logging.info(f"Status do login: {resposta_login.status_code}")
                
                # Verifica o status da resposta
                if resposta_login.status_code == 403:
                    logging.warning(f"Tentativa {tentativas + 1}/{max_tentativas} falhou. Aguardando...")
                    time.sleep(random.uniform(30, 60))
                    tentativas += 1
                    continue
                
                if resposta_login.status_code != 200:
                    raise Exception(f"Erro no login. Status: {resposta_login.status_code}")
                
                # Verifica se o login foi bem-sucedido
                if 'feed' not in self.sessao.get("https://www.linkedin.com").url:
                    raise Exception("Erro no login. Verifique suas credenciais.")
                
                logging.info("Login realizado com sucesso!")
                return
            
            except Exception as e:
                logging.error(f"Erro na tentativa {tentativas + 1}: {e}")
                tentativas += 1
                time.sleep(random.uniform(30, 60))
                logging.error("Máximo de tentativas de login alcançado")
                raise Exception("Máximo de tentativas de login alcançado")
    
    def _montar_url_busca(self, palavras_chave: List[str], 
                         experiencia_minima: int, localizacao: str, 
                         pagina: int) -> str:
        """Monta a URL de busca com os parâmetros fornecidos"""
        base_url = "https://www.linkedin.com/search/results/people/"
        query = f"?keywords={' AND '.join(palavras_chave)}"
        
        if experiencia_minima > 0:
            query += f"&experience={experiencia_minima}"
        if localizacao:
            query += f"&location={localizacao.replace(' ', '%20')}"
        query += f"&page={pagina}"
        query += "&currentCompany=none"
        query += "&pastCompany=none"
        query += "&school=none"
        query += "&profileLanguage=pt"
        query += "&type=PEOPLE_AND_COMPANIES"
        
        return base_url + query
    
    def buscar_candidatos(self, palavras_chave: List[str], 
                         experiencia_minima: int = 2,
                         localizacao: str = None,
                         quantidade: int = 100) -> List[Dict]:
        """Busca candidatos no LinkedIn baseado nas palavras-chave"""
        logging.info(f"Iniciando busca com palavras-chave: {palavras_chave}")
        candidatos = []
        pagina_atual = 0
        
        while len(candidatos) < quantidade:
            try:
                # Monta a URL de busca
                url_busca = self._montar_url_busca(palavras_chave,
                                                 experiencia_minima,
                                                 localizacao,
                                                 pagina_atual)
                logging.info(f"Buscando página {pagina_atual + 1}: {url_busca}")
                
                # Faz a requisição
                resposta = self.sessao.get(url_busca)
                logging.info(f"Status da busca: {resposta.status_code}")
                
                soup = BeautifulSoup(resposta.text, 'html.parser')
                perfis = soup.find_all('div', {'class': 'search-result__result-link'})
                logging.info(f"Encontrados {len(perfis)} perfis na página")
                
                if not perfis:
                    logging.info("Nenhum perfil encontrado. Finalizando busca.")
                    break
                
                # Coleta informações de cada perfil
                for perfil in perfis:
                    url_perfil = perfil.get('href')
                    if not url_perfil or not url_perfil.startswith('https://www.linkedin.com/in/'):
                        continue
                    
                    # Obtém detalhes do perfil
                    dados_candidato = self._extrair_dados(url_perfil)
                    logging.info(f"Extraindo dados do perfil: {url_perfil}")
                    
                    if dados_candidato:
                        self.salvar_candidato_db(dados_candidato)
                        candidatos.append(dados_candidato)
                        logging.info(f"Candidato adicionado. Total: {len(candidatos)}")
                
                if len(candidatos) >= quantidade:
                    logging.info("Quantidade desejada atingida. Finalizando busca.")
                    break
                
                pagina_atual += 1
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                logging.error(f"Erro na busca: {e}")
                break
        
        logging.info(f"Busca concluída. Total de candidatos encontrados: {len(candidatos)}")
        return candidatos[:quantidade]
    
    def _extrair_dados(self, url_perfil: str) -> Dict:
        """Extrai os dados de um perfil do LinkedIn"""
        try:
            # Obtém o perfil
            resposta = self.sessao.get(url_perfil)
            soup = BeautifulSoup(resposta.text, 'html.parser')
            
            return {
                'nome': self._extrair_nome(soup),
                'titulo': self._extrair_titulo(soup),
                'empresa': self._extrair_empresa(soup),
                'localizacao': self._extrair_localizacao(soup),
                'experiencia': self._extrair_experiencia(soup)
            }
            
        except Exception as e:
            logging.error(f"Erro ao extrair dados do perfil {url_perfil}: {e}")
            return {}
    
    def _extrair_nome(self, soup: BeautifulSoup) -> str:
        """Extrai o nome do perfil"""
        elemento = soup.find('h1', {'class': 't-24 t-bold'})
        return elemento.text.strip() if elemento else ''
    
    def _extrair_titulo(self, soup: BeautifulSoup) -> str:
        """Extrai o título atual"""
        elemento = soup.find('div', {'class': 'text-body-medium break-words'})
        return elemento.text.strip() if elemento else ''
    
    def _extrair_empresa(self, soup: BeautifulSoup) -> str:
        """Extrai a empresa atual"""
        elemento = soup.find('div', {'class': 'text-body-small'})
        return elemento.text.strip() if elemento else ''
    
    def _extrair_localizacao(self, soup: BeautifulSoup) -> str:
        """Extrai a localização"""
        elemento = soup.find('span', {'class': 'text-body-small'})
        return elemento.text.strip() if elemento else ''
    
    def _extrair_experiencia(self, soup: BeautifulSoup) -> str:
        """Extrai a experiência"""
        elemento = soup.find('span', {'class': 'mr1 t-normal'})
        return elemento.text.strip() if elemento else ''
    
    def salvar_resultados(self, candidatos: List[Dict], arquivo_saida: str):
        """Salva os resultados em um arquivo CSV"""
        df = pd.DataFrame(candidatos)
        df.to_csv(arquivo_saida, index=False)
        logging.info(f"Resultados salvos em {arquivo_saida}")

def exemplo_uso():
    # Configuração das credenciais
    email = "mateusedavi2016@gmail.com"
    senha = "retyro17"
    
    # Lista de proxies (exemplo)
    proxies = [
        "http://proxy1:8080",
        "http://proxy2:8080",
        "http://proxy3:8080"
    ]
    
    # Criar instância do buscador
    buscador = BuscadorCandidatosLinkedIn(email, senha, proxies)
    
    # Palavras-chave para busca
    palavras_chave = [
        "desenvolvedor Full Stack",
        "goland",
        "backend"
        "Java"
        "Angular.js"
    ]
    
    # Buscar candidatos
    candidatos = buscador.buscar_candidatos(
        palavras_chave=palavras_chave,
        experiencia_minima=2,
        localizacao="Mato Grosso, Brasil",
        quantidade=50
    )
    
    # Salvar resultados
    buscador.salvar_resultados(candidatos, "candidatos_encontrados.csv")

if __name__ == "__main__":
    exemplo_uso()