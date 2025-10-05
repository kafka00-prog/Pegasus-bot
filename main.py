#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
from datetime import datetime, timedelta
from colorama import Fore, Style, init
from collections import deque
import requests
import re
import threading

init(autoreset=True)

# ======================== CONFIGURAÇÕES ========================
URL_SITE = "https://www.tipminer.com/br/historico/blaze/double"

gatilhos = {
    7: ("vermelho", 4),
    3: ("vermelho", 5),
    10: ("preto", 2),
    14: ("preto", 5)
}

TOKEN_TELEGRAM = "8380470685:AAGF9TNKOucci3QtUgFcw8J2tWNm-LDmGUY"
CHAT_ID = -1002923223605

ultimos_ids = deque(maxlen=50)
sinal_ativo = None
pedras_minuto_atual = []

# Estatísticas
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
        return "branco"  # ✅ reconhecimento do zero
    elif 1 <= numero <= 7:
        return "vermelho"
    return "preto"

def pegar_ultimo_resultado(driver):
    try:
        # ✅ Captura tanto números normais quanto o zero (branco)
        cells = driver.find_elements(By.CSS_SELECTOR, ".cell--double, .cell--lucky")
        if not cells:
            return None

        cell = cells[0]
        class_attr = cell.get_attribute("class") or ""
        match_id = re.search(r"data-id-([a-f0-9]+)", class_attr)
        data_id = match_id.group(1) if match_id else None

        numero_elem = cell.find_element(By.CSS_SELECTOR, ".cell__result")
        numero_text = numero_elem.text.strip()

        # ✅ Tratamento especial para branco (zero)
        if numero_text == "" or numero_text == "0":
            numero_int = 0
        else:
            if not numero_text.isdigit():
                return None
            numero_int = int(numero_text)

        hora_elem = cell.find_element(By.CSS_SELECTOR, ".cell__date")
        hora = hora_elem.text.strip()

        return {
            "data_id": data_id,
            "numero": numero_int,
            "cor": cor_para_texto(numero_int),
            "hora": hora
        }
    except Exception as e:
        print(Fore.RED + f"Erro ao capturar resultado: {e}" + Style.RESET_ALL)
        return None

def formatar_sinal_telegram(minuto, cor):
    cor_emoji = "🔴" if cor == "vermelho" else "⚫️"
    return (f"🚨 <b>SINAL DETECTADO</b>\n"
            f"🕒 Minuto: <b>{minuto}</b>\n"
            f"🎯 Cor: <b>{cor.capitalize()} {cor_emoji}⚪️</b>\n"
            f"💰 G1 se necessário")

def enviar_relatorio():
    while True:
        time.sleep(300)  # envia a cada 5 minutos
        msg = (f"📊 <b>Relatório Parcial</b>\n\n"
               f"✅ WIN: {estatisticas['win']}\n"
               f"✅ G1 WIN: {estatisticas['g1_win']}\n"
               f"❌ LOSS: {estatisticas['loss']}\n"
               f"📈 Assertividade: {calcular_assertividade():.2f}%")
        enviar_telegram(msg)

def calcular_assertividade():
    total = estatisticas["win"] + estatisticas["g1_win"] + estatisticas["loss"]
    if total == 0:
        return 0
    return ((estatisticas["win"] + estatisticas["g1_win"]) / total) * 100

# ======================== MONITORAMENTO ========================
def monitorar_site():
    global sinal_ativo, pedras_minuto_atual

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver = webdriver.Chrome(options=options)
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

            # 1 - Detecta Gatilho
            if numero in gatilhos and sinal_ativo is None:
                cor, delay = gatilhos[numero]
                minuto_sinal = (datetime.strptime(minuto_pedra, "%H:%M") + timedelta(minutes=delay)).strftime("%H:%M")
                sinal_ativo = {"minuto": minuto_sinal, "cor": cor, "g1": False}
                pedras_minuto_atual = []
                print(Fore.GREEN + f"🚨 Gatilho detectado | Sinal para {minuto_sinal} | Cor: {cor}" + Style.RESET_ALL)
                enviar_telegram(formatar_sinal_telegram(minuto_sinal, cor))

            # 2 - Monitoramento do minuto do sinal
            if sinal_ativo and minuto_pedra == sinal_ativo['minuto']:
                pedras_minuto_atual.append(ultimo)

                # Primeira pedra
                if len(pedras_minuto_atual) == 1:
                    if cor_real == sinal_ativo['cor']:
                        estatisticas['win'] += 1
                        print(Fore.GREEN + "✅ WIN na primeira pedra!" + Style.RESET_ALL)
                        enviar_telegram(f"✅ WIN - Cor: {cor_real} | Número: {numero}")
                        sinal_ativo = None
                        pedras_minuto_atual = []
                    elif cor_real == "branco":
                        estatisticas['win'] += 1
                        print(Fore.CYAN + "⚪️ WIN no ZERO (branco)!" + Style.RESET_ALL)
                        enviar_telegram(f"⚪️ WIN no ZERO (Branco) - Número: {numero}")
                        sinal_ativo = None
                        pedras_minuto_atual = []
                    else:
                        print(Fore.YELLOW + "⚠️ Primeira pedra não bateu, aguardando G1..." + Style.RESET_ALL)
                        sinal_ativo['g1'] = True

                # G1 (segunda pedra)
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
                    sinal_ativo = None
                    pedras_minuto_atual = []

            time.sleep(2)

        except Exception as e:
            print(Fore.RED + f"Erro no monitoramento: {e}" + Style.RESET_ALL)
            time.sleep(3)

# ======================== EXECUÇÃO ========================
if __name__ == "__main__":
    threading.Thread(target=enviar_relatorio, daemon=True).start()
    monitorar_site()
