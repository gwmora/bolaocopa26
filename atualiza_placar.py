import os
import re
import json
import requests
import unicodedata

# 1. Puxa a chave de segurança que você guardou no GitHub
API_TOKEN = os.environ.get('API_TOKEN', '').strip()
if not API_TOKEN:
    print("API_TOKEN não encontrado.")
    exit(1)

# 2. Dicionário de tradução
TEAM_MAP = {
    "Mexico": "México", "South Africa": "África do Sul", "South Korea": "Coreia do Sul",
    "Czech Republic": "Tchéquia", "Czechia": "Tchéquia", "Canada": "Canadá",
    "Bosnia and Herzegovina": "Bósnia", "Bosnia": "Bósnia", "Qatar": "Catar",
    "Switzerland": "Suíça", "Brazil": "Brasil", "Morocco": "Marrocos",
    "Haiti": "Haiti", "Scotland": "Escócia", "United States": "EUA",
    "USA": "EUA", "Paraguay": "Paraguai", "Australia": "Austrália",
    "Turkey": "Turquia", "Germany": "Alemanha", "Curaçao": "Curaçao",
    "Ivory Coast": "Costa do Marfim", "Cote d'Ivoire": "Costa do Marfim",
    "Ecuador": "Equador", "Netherlands": "Holanda", "Japan": "Japão",
    "Sweden": "Suécia", "Tunisia": "Tunísia", "Iran": "Irã",
    "New Zealand": "Nova Zelândia", "Belgium": "Bélgica", "Egypt": "Egito",
    "Spain": "Espanha", "Cape Verde": "Cabo Verde", "Saudi Arabia": "Arábia Saudita",
    "Uruguay": "Uruguai", "France": "França", "Senegal": "Senegal",
    "Iraq": "Iraque", "Norway": "Noruega", "Argentina": "Argentina",
    "Algeria": "Argélia", "Austria": "Áustria", "Jordan": "Jordânia",
    "Portugal": "Portugal", "DR Congo": "RD Congo", "Congo DR": "RD Congo",
    "Uzbekistan": "Uzbequistão", "Colombia": "Colômbia", "England": "Inglaterra",
    "Croatia": "Croácia", "Panama": "Panamá", "Ghana": "Gana"
}

def norm(name):
    if name is None: return ""
    return unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8').lower()

# 3. Lê o seu arquivo HTML
html_path = 'index.html'
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# 4. Entende as IDs dos jogos dinamicamente
match_d = re.search(r'const D\s*=\s*(\{.*?\});', html, re.DOTALL)
if not match_d:
    print("Variável de dados não encontrada no HTML.")
    exit(1)

D = json.loads(match_d.group(1))
games_map = {}
for g in D['g']:
    id_jogo = g[0]
    t1 = norm(g[3])
    t2 = norm(g[4])
    games_map[f"{t1}x{t2}"] = id_jogo
    games_map[f"{t2}x{t1}"] = id_jogo

# 5. Chama a API
url = "https://api.football-data.org/v4/competitions/WC/matches"
headers = {"X-Auth-Token": API_TOKEN}
response = requests.get(url, headers=headers)

if response.status_code != 200:
    print(f"Erro na API: {response.status_code}")
    exit(1)

data = response.json()
matches = data.get('matches', [])

# 6. Preserva os resultados existentes
novos_resultados = {}
old_hc_match = re.search(r'const HC = (\{.*?\});', html)
if old_hc_match:
    hc_str = re.sub(r'(\d+):', r'"\1":', old_hc_match.group(1))
    antigos = json.loads(hc_str)
    novos_resultados = {int(k): v for k, v in antigos.items()}

# 7. Injeta os resultados que terminaram
for m in matches:
    if m.get('status') == 'FINISHED':
        home_en = m['homeTeam'].get('name')
        away_en = m['awayTeam'].get('name')
        
        # --- CORREÇÃO MANUAL PARA ESPANHA ---
        if home_en == "Spain" and away_en == "Saudi Arabia":
            score_home = 4
            score_away = 0
        else:
            score_home = m.get('score', {}).get('fullTime', {}).get('home')
            score_away = m.get('score', {}).get('fullTime', {}).get('away')
        # ------------------------------------
        
        if score_home is not None and score_away is not None:
            h_name = TEAM_MAP.get(home_en, home_en)
            a_name = TEAM_MAP.get(away_en, away_en)
            
            home_pt = norm(h_name)
            away_pt = norm(a_name)
            
            chave = f"{home_pt}x{away_pt}"
            chave_inv = f"{away_pt}x{home_pt}"
            
            if chave in games_map:
                novos_resultados[games_map[chave]] = [score_home, score_away]
            elif chave_inv in games_map:
                novos_resultados[games_map[chave_inv]] = [score_away, score_home]

# 8. Sobrescreve o HTML com os placares e a data atual
if novos_resultados:
    # (Manter o seu código anterior de replace do HC aqui...)
    
    # Adicionar agora a atualização da data:
    from datetime import datetime, timedelta
    hora_atual = (datetime.utcnow() - timedelta(hours=3)).strftime("%d/%m/%Y às %H:%M")
    html = re.sub(r'<span id="last-update">.*?</span>', f'<span id="last-update">{hora_atual}</span>', html)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Sucesso! {len(novos_resultados)} jogos finalizados processados.")
