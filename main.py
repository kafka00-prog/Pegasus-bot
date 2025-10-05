#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
from datetime import datetime, timedelta
from colorama import Fore, Style, init
from collections import deque
import requests
import re
import os

init(autoreset=True)

# ======================== CONFIGURAÇÕES ========================
URL_SITE = "https://www.tipminer.com/br/historico/blaze/double"

gatilhos = {
    7: ("vermelho", 4),
    3: ("vermelho", 5),
    10: ("preto", 2),
    14: ("preto", 5)
}

# 🔒 Token privado e chat ID direto no código (ok se o repositório for privado)
TOKEN_TELEGRAM = "8380470685:AAGF9TNKOucci3QtUgFcw8J2tWNm-LDmGUY"
CHAT_ID = -1002923223605

ultimos_ids = deque(maxlen=50)
sinal_ativo = None
pedras_minuto_atual = []

estatisticas = {"win": 0, "g1_win": 0, "loss": 0}

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

def pegar_ultimo_resultado(driver):
    try:
        cells = driver.find_elements(By.CSS_SELECTOR, ".cell--double, .cell--lucky, .cell--wild")
        if not cells:
            return None

        for cell in cells:
            class_attr = cell.get_attribute("class") or ""
            match_id = re.search(r"data-id-([^\s]+)", class_attr)
            data_id = match_id.group(1) if match_id else None

            # Ignorar células inválidas ou placeholders
            if not data_id or "/" in data_id or "wild" in class_attr:
                continue

            numero_elem = cell.find_element(By.CSS_SELECTOR, ".cell__result")
            numero_text = numero_elem.text.strip()
            if numero_text == "":
                continue

            if numero_text == "0":
                numero_int = 0
            elif numero_text.isdigit():
                numero_int = int(numero_text)
            else:
                continue

            hora_elem = cell.find_element(By.CSS_SELECTOR, ".cell__date")
            hora = hora_elem.text.strip()
            if "99" in hora or hora == "":
                continue

            return {
                "data_id": data_id,
                "numero": numero_int,
                "cor": cor_para_texto(numero_int),
                "hora": hora
            }

        return None

    except Exception as e:
        print(Fore.RED + f"Erro ao capturar resultado: {e}" + Style.RESET_ALL)
        return None

def formatar_sinal_telegram(minuto, cor):
    cor_emoji = "🔴" if cor == "vermelho" else "⚫️"
    return (f"🚨 <b>SINAL DETECTADO</b>\n"
            f"🕒 Minuto: <b>{minuto}</b>\n"
            f"🎯 Cor: <b>{cor.capitalize()} {cor_emoji}⚪️</b>\n"
            f"💰 G1 se necessário")

def calcular_assertividade():
    total = estatisticas["win"] + estatisticas["g1_win"] + estatisticas["loss"]
    if total == 0:
        return 0
    return ((estatisticas["win"] + estatisticas["g1_win"]) / total) * 100

def enviar_relatorio():
    msg = (f"📊 <b>Relatório Parcial</b>\n\n"
           f"✅ WIN: {estatisticas['win']}\n"
           f"✅ G1 WIN: {estatisticas['g1_win']}\n"
           f"❌ LOSS: {estatisticas['loss']}\n"
           f"📈 Assertividade: {calcular_assertividade():.2f}%")
    enviar_telegram(msg)

# ======================== MONITORAMENTO ========================
def monitorar_site():
    global sinal_ativo, pedras_minuto_atual

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    chrome_path = os.getenv("CHROME_PATH", "/usr/bin/chromium")
    driver_path = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
    options.binary_location = chrome_path

    # ✅ Compatível com Selenium 4+
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(URL_SITE)
    time.sleep(3)
    print(Fore.YELLOW + "🔄 Monitorando resultados..." + Style.RESET_ALL)

    while True:
        try:
            ultimo = pegar_ultimo_resultado(driver)
            if not ultimo:
                time.sleep(2)
                continue

            if ultimo['data_id'] in ultimos_ids:
                time.sleep(2)
                continue
            ultimos_ids.append(ultimo['data_id'])

            numero = ultimo['numero']
            cor_real = ultimo['cor']
            minuto_pedra = ultimo['hora']

            # Detecta gatilho
            if numero in gatilhos and sinal_ativo is None:
                cor, delay = gatilhos[numero]
                minuto_sinal = (datetime.strptime(minuto_pedra, "%H:%M") + timedelta(minutes=delay)).strftime("%H:%M")
                sinal_ativo = {"minuto": minuto_sinal, "cor": cor, "g1": False}
                pedras_minuto_atual = []
                print(Fore.GREEN + f"🚨 Gatilho detectado | Sinal para {minuto_sinal} | Cor: {cor}" + Style.RESET_ALL)
                enviar_telegram(formatar_sinal_telegram(minuto_sinal, cor))

            # Verifica o minuto do sinal
            if sinal_ativo and minuto_pedra == sinal_ativo['minuto']:
                pedras_minuto_atual.append(ultimo)

                if len(pedras_minuto_atual) == 1:
                    if cor_real == sinal_ativo['cor']:
                        estatisticas['win'] += 1
                        print(Fore.GREEN + "✅ WIN na primeira pedra!" + Style.RESET_ALL)
                        enviar_telegram(f"✅ WIN - Cor: {cor_real} | Número: {numero}")
                        enviar_relatorio()
                        sinal_ativo = None
                        pedras_minuto_atual = []
                    elif cor_real == "branco":
                        estatisticas['win'] += 1
                        print(Fore.CYAN + "⚪️ WIN no ZERO (branco)!" + Style.RESET_ALL)
                        enviar_telegram(f"⚪️ WIN no ZERO (Branco) - Número: {numero}")
                        enviar_relatorio()
                        sinal_ativo = None
                        pedras_minuto_atual = []
                    else:
                        print(Fore.YELLOW + "⚠️ Primeira pedra não bateu, aguardando G1..." + Style.RESET_ALL)
                        sinal_ativo['g1'] = True

                elif len(pedras_minuto_atual) == 2 and sinal_ativo:
                    if cor_real == sinal_ativo['cor']:
                        estatisticas['g1_win'] += 1
                        print(Fore.GREEN + "✅ G1 WIN na segunda pedra!" + Style.RESET_ALL)
                        enviar_telegram(f"✅ G1 WIN - Cor: {cor_real} | Número: {numero}")
                    elif cor_real == "branco":
                        estatisticas['g1_win'] += 1
                        print(Fore.CYAN + "⚪️ G1 WIN no ZERO (branco)!" + Style.RESET_ALL)
                        enviar_telegram(f"⚪️ G1 WIN no ZERO (Branco) - Número: {numero}")
                    else:
                        estatisticas['loss'] += 1
                        print(Fore.RED + "❌ LOSS após G1!" + Style.RESET_ALL)
                        enviar_telegram(f"❌ LOSS - Cor: {cor_real} | Número: {numero}")
                    enviar_relatorio()
                    sinal_ativo = None
                    pedras_minuto_atual = []

            time.sleep(2)

        except Exception as e:
            print(Fore.RED + f"Erro no monitoramento: {e}" + Style.RESET_ALL)
            time.sleep(3)

# ======================== EXECUÇÃO ========================
if __name__ == "__main__":
    monitorar_site()
