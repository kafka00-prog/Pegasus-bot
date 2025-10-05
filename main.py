#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime, timedelta
from colorama import Fore, Style, init
from collections import deque
import requests
import re

init(autoreset=True)

# ======================== CONFIGURAÇÕES ========================
URL_SITE = "https://www.tipminer.com/br/historico/blaze/double"

gatilhos = {
    7: ("vermelho", 4),
    12: ("preto", 3)
}

TOKEN_TELEGRAM = "8380470685:AAGF9TNKOucci3QtUgFcw8J2tWNm-LDmGUY"
CHAT_ID = -1002923223605

# ======================== VARIÁVEIS GLOBAIS ========================
ultimos_ids = deque(maxlen=50)
sinal_ativo = None
pedras_minuto_atual = []
estatisticas = {"win": 0, "g1_win": 0, "loss": 0}
historico_cores = deque(maxlen=10)

# ======================== FUNÇÕES AUXILIARES ========================
def enviar_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(Fore.RED + f"Erro ao enviar Telegram: {e}" + Style.RESET_ALL)

def cor_para_texto(numero):
    if numero == 0:
        return "branco"
    elif 1 <= numero <= 7:
        return "vermelho"
    return "preto"

# ======================== FUNÇÃO PEGA RESULTADO SEGURA ========================
def pegar_ultimo_resultado(driver):
    try:
        cells = driver.find_elements(By.CSS_SELECTOR, ".cell--double, .cell--lucky")
        if not cells:
            return None
        cell = cells[0]

        # Captura número com espera
        try:
            numero_elem = WebDriverWait(cell, 1).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".cell__result"))
            )
            numero_text = numero_elem.text.strip()
        except:
            return None

        # Captura hora
        try:
            hora_elem = cell.find_element(By.CSS_SELECTOR, ".cell__date")
            hora = hora_elem.text.strip()
        except:
            return None

        # Ignorar células sem número válido ou virada de dia
        if not numero_text.isdigit() or "99" in hora:
            return None

        numero_int = int(numero_text)
        class_attr = cell.get_attribute("class") or ""
        match_id = re.search(r"data-id-([a-f0-9/]+)", class_attr)
        data_id = match_id.group(1) if match_id else None

        return {
            "data_id": data_id,
            "numero": numero_int,
            "cor": cor_para_texto(numero_int),
            "hora": hora
        }

    except Exception as e:
        print(Fore.RED + f"Erro ao capturar resultado (render): {e}" + Style.RESET_ALL)
        return None

def formatar_sinal_telegram(minuto, cor):
    cor_emoji = "🔴" if cor == "vermelho" else "⚫️"
    return (f"🚨 <b>SINAL DETECTADO</b>\n"
            f"🕒 Minuto: <b>{minuto}</b>\n"
            f"🎯 Cor: <b>{cor.capitalize()} {cor_emoji}⚪️</b>\n"
            f"💰 G1 se necessário")

# ======================== ESTRATÉGIA ========================
def verificar_gatilhos(numero, minuto_pedra):
    global sinal_ativo, pedras_minuto_atual
    if numero in gatilhos and sinal_ativo is None:
        cor, delay = gatilhos[numero]
        minuto_sinal = (datetime.strptime(minuto_pedra, "%H:%M") + timedelta(minutes=delay)).strftime("%H:%M")
        sinal_ativo = {"minuto": minuto_sinal, "cor": cor, "g1": False}
        pedras_minuto_atual = []
        enviar_telegram(formatar_sinal_telegram(minuto_sinal, cor))
        print(Fore.GREEN + f"🚨 Gatilho detectado | Sinal para {minuto_sinal} | Cor: {cor}" + Style.RESET_ALL)

def verificar_quebra(minuto_pedra):
    global sinal_ativo, pedras_minuto_atual, historico_cores
    if len(historico_cores) < 3 or sinal_ativo is not None:
        return
    penultima_cor, penultimo_minuto = historico_cores[-2]
    ultima_cor, ultimo_minuto = historico_cores[-1]
    if ultima_cor != penultima_cor:
        sequencia = 1
        for cor, _ in reversed(list(historico_cores)[:-1]):
            if cor == penultima_cor:
                sequencia += 1
            else:
                break
        if sequencia >= 2:
            minuto_sinal = (datetime.strptime(ultimo_minuto, "%H:%M") + timedelta(minutes=2)).strftime("%H:%M")
            cor_sinal = penultima_cor
            sinal_ativo = {"minuto": minuto_sinal, "cor": cor_sinal, "g1": False}
            pedras_minuto_atual = []
            enviar_telegram(formatar_sinal_telegram(minuto_sinal, cor_sinal))
            print(Fore.MAGENTA + f"🎯 Quebra detectada | Sequência {sequencia} {cor_sinal} | Sinal às {minuto_sinal}" + Style.RESET_ALL)

def verificar_preto(minuto_pedra):
    global sinal_ativo, pedras_minuto_atual, historico_cores
    if len(historico_cores) < 3 or sinal_ativo is not None:
        return
    penultima_cor, penultimo_minuto = historico_cores[-2]
    ultima_cor, ultimo_minuto = historico_cores[-1]
    if penultima_cor == "preto" and ultima_cor in ["vermelho", "branco"]:
        sequencia = 1
        for cor, _ in reversed(list(historico_cores)[:-1]):
            if cor == "preto":
                sequencia += 1
            else:
                break
        if sequencia >= 2:
            minuto_sinal = (datetime.strptime(penultimo_minuto, "%H:%M") + timedelta(minutes=2)).strftime("%H:%M")
            cor_sinal = "preto"
            sinal_ativo = {"minuto": minuto_sinal, "cor": cor_sinal, "g1": False}
            pedras_minuto_atual = []
            enviar_telegram(formatar_sinal_telegram(minuto_sinal, cor_sinal))
            print(Fore.BLUE + f"⚫ Estratégia Preto | Sequência {sequencia} preta quebrada por {ultima_cor} | Sinal preto às {minuto_sinal}" + Style.RESET_ALL)

# ======================== MONITORAMENTO ========================
def monitorar_site():
    global sinal_ativo, pedras_minuto_atual, historico_cores
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    driver.get(URL_SITE)
    time.sleep(3)
    print(Fore.YELLOW + "🔄 Monitorando resultados..." + Style.RESET_ALL)

    while True:
        try:
            ultimo = pegar_ultimo_resultado(driver)
            if not ultimo or ultimo['data_id'] in ultimos_ids:
                time.sleep(2)
                continue
            ultimos_ids.append(ultimo['data_id'])

            numero = ultimo['numero']
            cor_real = ultimo['cor']
            minuto_pedra = ultimo['hora']

            if cor_real != "branco":
                historico_cores.append((cor_real, minuto_pedra))
                histo_texto = " -> ".join([f"{cor.capitalize()}({minuto})" for cor, minuto in historico_cores])
                print(Fore.CYAN + "📜 Histórico (últimos 10): " + histo_texto + Style.RESET_ALL)

            # Avaliar estratégias
            verificar_gatilhos(numero, minuto_pedra)
            verificar_quebra(minuto_pedra)
            verificar_preto(minuto_pedra)

            # Avaliação WIN/G1/Loss
            if sinal_ativo and minuto_pedra == sinal_ativo['minuto']:
                pedras_minuto_atual.append(ultimo)
                if len(pedras_minuto_atual) == 1:
                    if cor_real == sinal_ativo['cor'] or cor_real == "branco":
                        estatisticas['win'] += 1
                        msg = "⚪️ WIN no ZERO (branco)!" if cor_real == "branco" else "✅ WIN na primeira pedra!"
                        print(Fore.GREEN + msg + Style.RESET_ALL)
                        enviar_telegram(f"{msg} - Cor: {cor_real} | Número: {numero}")
                        sinal_ativo = None
                        pedras_minuto_atual = []
                    else:
                        print(Fore.YELLOW + "⚠️ Primeira pedra não bateu, aguardando G1..." + Style.RESET_ALL)
                        sinal_ativo['g1'] = True
                elif len(pedras_minuto_atual) == 2 and sinal_ativo:
                    if cor_real == sinal_ativo['cor'] or cor_real == "branco":
                        estatisticas['g1_win'] += 1
                        msg = "⚪️ G1 WIN no ZERO (branco)!" if cor_real == "branco" else "✅ G1 WIN na segunda pedra!"
                        print(Fore.GREEN + msg + Style.RESET_ALL)
                        enviar_telegram(f"{msg} - Cor: {cor_real} | Número: {numero}")
                    else:
                        estatisticas['loss'] += 1
                        print(Fore.RED + "❌ LOSS após G1!" + Style.RESET_ALL)
                        enviar_telegram(f"❌ LOSS - Cor: {cor_real} | Número: {numero}")
                    sinal_ativo = None
                    pedras_minuto_atual = []

            time.sleep(2)
        except Exception as e:
            print(Fore.RED + f"Erro no monitoramento: {e}" + Style.RESET_ALL)
            time.sleep(3)

# ======================== MAIN ========================
if __name__ == "__main__":
    monitorar_site()
