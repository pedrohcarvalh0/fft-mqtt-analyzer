#!/usr/bin/env python3
"""
Script para testar a conexão MQTT antes de executar o analisador principal
"""

import paho.mqtt.client as mqtt
import time
import sys

def test_mqtt_connection(broker_host="192.168.0.103", broker_port=1883, username="admin", password="123456"):
    """Testa a conexão MQTT com o broker"""
    
    print("🔍 Testando conexão MQTT...")
    print(f"📡 Broker: {broker_host}:{broker_port}")
    print(f"👤 Credenciais: {username}/{'*' * len(password)}")
    
    # Variáveis de controle
    connection_result = {"connected": False, "error": None}
    messages_received = []
    
    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            print("✅ Conexão MQTT bem-sucedida!")
            connection_result["connected"] = True
            
            # Subscrever a todos os tópicos para teste
            topics = ["/temperature", "/humidity", "/temperature/fft", "/humidity/fft", "/online"]
            for topic in topics:
                client.subscribe(topic)
                print(f"📡 Subscrito ao tópico: {topic}")
                
        else:
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable", 
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorized"
            }
            error_msg = error_messages.get(rc, f"Unknown error code: {rc}")
            print(f"❌ Falha na conexão MQTT: {error_msg}")
            connection_result["error"] = error_msg
    
    def on_message(client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        timestamp = time.strftime('%H:%M:%S')
        
        message_info = f"[{timestamp}] {topic}: {payload}"
        messages_received.append(message_info)
        print(f"📨 {message_info}")
    
    def on_disconnect(client, userdata, rc, properties=None):
        if rc != 0:
            print(f"🔌 Desconexão inesperada: {rc}")
        else:
            print("🔌 Desconectado normalmente")
    
    # Criar cliente MQTT
    try:
        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        client.username_pw_set(username, password)
        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect
        
        print("🔄 Tentando conectar...")
        client.connect(broker_host, broker_port, 60)
        client.loop_start()
        
        # Aguardar conexão
        timeout = 10
        start_time = time.time()
        while not connection_result["connected"] and connection_result["error"] is None:
            if time.time() - start_time > timeout:
                print("⏰ Timeout na conexão MQTT")
                break
            time.sleep(0.1)
        
        if connection_result["connected"]:
            print(f"⏱️ Aguardando mensagens por 30 segundos...")
            print("   (O RP2040 publica dados a cada 2 segundos)")
            
            # Aguardar mensagens
            time.sleep(30)
            
            print(f"\n📊 RESULTADO DO TESTE:")
            print(f"✅ Conexão: {'OK' if connection_result['connected'] else 'FALHOU'}")
            print(f"📨 Mensagens recebidas: {len(messages_received)}")
            
            if len(messages_received) > 0:
                print("📋 Últimas mensagens:")
                for msg in messages_received[-5:]:  # Mostrar últimas 5
                    print(f"   {msg}")
                print("✅ Comunicação MQTT funcionando!")
                return True
            else:
                print("⚠️ Nenhuma mensagem recebida do RP2040")
                print("   Possíveis problemas:")
                print("   1. RP2040 não está conectado ao WiFi")
                print("   2. RP2040 não está executando o código")
                print("   3. RP2040 não consegue conectar ao broker MQTT")
                print("   4. Tópicos MQTT diferentes")
                return False
        else:
            print(f"❌ Falha na conexão: {connection_result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        return False
    finally:
        try:
            client.loop_stop()
            client.disconnect()
        except:
            pass

if __name__ == "__main__":
    print("🧪 TESTE DE CONEXÃO MQTT")
    print("=" * 50)
    
    success = test_mqtt_connection()
    
    if success:
        print("\n🎉 Teste bem-sucedido! Você pode executar o analisador principal.")
        sys.exit(0)
    else:
        print("\n❌ Teste falhou. Verifique a configuração antes de continuar.")
        sys.exit(1)
