# -*- coding: utf-8 -*-
"""
Created on Sat May 18 10:00:54 2024

@author: marco
"""

import time
import json
import os
import RPi.GPIO as GPIO
import smbus2
from datetime import datetime
import requests

CLIENT_ID = "asdqwesdasds"
UNIT_INDEX = 1

# indirizzo sul bus i2c
DS1307_ADDRESS = 0x68


# inizializzazioe bus i2c
bus = smbus2.SMBus(1)

def resettamux():
    global clk_pin
    global enable_pin
    global reset_pin
    global num_4017
# Definisce i pin di GPIO per clock, enable e reset del 4017
    clk_pin = 16
    enable_pin = 20
    reset_pin = 19

# Numero dei 4017
    num_4017 = 4

# inizializzazione GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(clk_pin, GPIO.OUT)
GPIO.setup(enable_pin, GPIO.OUT)
GPIO.setup(reset_pin, GPIO.OUT)

# Deselezione canali su singolo 4017
def deselect_4017():
    # CLK ed ENABLE a livello basso
    GPIO.output(clk_pin, GPIO.LOW)
    GPIO.output(enable_pin, GPIO.LOW)

    # Imposta RESET a livello basso
    GPIO.output(reset_pin, GPIO.LOW)
    # attesa
    time.sleep(0.1)
    # imposta pin RESET al livello alto
    GPIO.output(reset_pin, GPIO.HIGH)

# funzione per deselezionare tutti i canali sui 4 4017
def deselect_all_4017():
    for _ in range(num_4017):
        deselect_4017()
        time.sleep(0.1)  
        
def relespegni():
# impostazione gpio
    GPIO.setmode(GPIO.BCM)

# pin gpio 26 come uscita
gpio_pin = 26
GPIO.setup(gpio_pin, GPIO.OUT)

# pin gpio 26 a livello basso
GPIO.output(gpio_pin, GPIO.LOW)

# 
GPIO.cleanup()

def bcd_to_dec(bcd):
#    """Convert binary coded decimal to decimal."""
    return (bcd & 0x0F) + ((bcd >> 4) * 10)

def read_time():
#    """Read the current time from the DS1307 RTC module."""
    data = bus.read_i2c_block_data(DS1307_ADDRESS, 0x00, 7)
    seconds = bcd_to_dec(data[0] & 0x7F)
    minutes = bcd_to_dec(data[1])
    hours = bcd_to_dec(data[2] & 0x3F)  # ora nella forma 24h
    day = bcd_to_dec(data[4])
    month = bcd_to_dec(data[5])
    year = bcd_to_dec(data[6]) + 2000
    return datetime(year, month, day, hours, minutes, seconds)

def load_recorded_times(file_path):
#    """Load the recorded times from a file."""
    with open(file_path, 'r') as file:
        lines = file.readlines()
    recorded_times = [datetime.strptime(line.strip(), "%Y-%m-%d %H:%M:%S") for line in lines]
    return recorded_times

def check_time_match():
#    """Main function to check DS1307 time against the recorded times every 25 seconds."""
    recorded_times = load_recorded_times('recorded_time.txt')
    while True:
        current_time = read_time()
        if current_time in recorded_times:
# azione se match            print(f"Match found! Current time: {current_time}")
#            else:
#            print(f"No match. Current time: {current_time}")
             time.sleep(25)

# timestamp nella forma 2024-05-19 12:00:00

def resetuscite():
    pass


# Funzione per trasformare il valore letto in una tensione
def trasformare_valore_in_tensione(valori_adc, riferimento=5.0, risoluzione=1023):
    return [valore * (riferimento / risoluzione) for valore in valori_adc]

# Funzione per salvare il file JSON sulla SD
def salvare_su_sd(file_json, percorso="/path/to/sd", nome_file="dati_sensori.json"):
    percorso_completo = os.path.join(percorso, nome_file)
    with open(percorso_completo, 'w') as file:
        file.write(file_json)
    print(f"File salvato su SD: {percorso_completo}")

# Funzione per inviare la coda di file precedenti e il file JSON appena creato
def inviare_file(file_json, percorso="/path/to/sd"):
    # Inviare i file in coda
    for nome_file in os.listdir(percorso):
        percorso_completo = os.path.join(percorso, nome_file)
        with open(percorso_completo, 'r') as file:
            contenuto = file.read()
        if inviare_al_server(contenuto):
            os.remove(percorso_completo)
            print(f"File inviato e rimosso: {percorso_completo}")
        else:
            print(f"Invio fallito: {percorso_completo}")

    # Inviare il file corrente
    if inviare_al_server(file_json):
        print("File corrente inviato con successo")
    else:
        print("Invio del file corrente fallito, salvando su SD")
        salvare_su_sd(file_json)

def formattare_json(data, _time, temperature):
    btt_lev = 0 #Livello di batteria del raspberry
    btt_status_V = 0 #Stato della batteria del raspberry

    return {
        "clientId": CLIENT_ID,
        "unitNumber": UNIT_INDEX,
        "time": _time,
        "data": data,
        "stats": {"temp C°": temperature, "btt lev %": btt_lev, "btt status V": btt_status_V}
    }

# Funzione per inviare dati al server
def inviare_al_server(data_json):
    response = requests.post("https://us-central1-x-project-a5ecf.cloudfunctions.net/writeDataOnDB", json=dati_json)
    return response.ok
    

# Funzione principale del processo dei sensori
def processo_sensori():
    # Punto 3.1: Accendere il relè per alimentare tutti i sensori
    accendere_rele()
    
    # Punto 3.2: Aspettare 2 secondi
    time.sleep(2)
    
    # Punto 3.3: Attivare sequenzialmente i canali del mux da 1 a 8 e leggere dall'ADC
    dati_sensori = []
    for canale in range(1, 9):
        # Attivare canale (da implementare)
        time.sleep(0.5)
        valore = leggere_adc(canale)
        dati_sensori.append(valore)
    
    # Punto 3.4: Trasformare il valore letto in una tensione
    tensioni = trasformare_valore_in_tensione(dati_sensori)
    
    # Punto 3.5: Leggere la temperatura del sensore di temperatura a bordo della centralina
    temperatura = leggere_temperatura()
    
    # Punto 3.6: Formattare il file JSON da inviare al server
    file_json = formattare_json(tensioni, read_time().timestamp(), temperatura)
    
    # Punto 3.7: Assicurarsi che il modem risponda OK al comando AT
    while inviare_comando_at("AT") != "OK":
        time.sleep(1)
    
    # Punto 3.8: Verificare che il modem sia registrato in rete
    if not modem_registrato():
        for _ in range(10):
            if modem_registrato():
                break
            time.sleep(1)
        else:
            # Se non riesce a registrarsi, salva il file JSON sulla SD e salta al punto 2
            salvare_su_sd(file_json)
            return
    
    # Punto 3.10: Inviare la coda di file precedenti e il file JSON appena creato
    inviare_file(file_json)
    
    # Punto 3.11: Salta al punto 1 (da implementare in base alla logica dell'applicazione)
    # Punto 3.12: Se non siamo riusciti a contattare il server, salvare i file per tentare il reinvio
    # alla prossima occasione (gestione degli errori da implementare)

# Esegui il processo
processo_sensori()

def main():
    resettamux()
    relespegni()
    resetuscite()
    read_time()

if __name__ == "__main__":
    main()