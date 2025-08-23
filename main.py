import socket
import ssl
import json
import re
import pycountry
import time
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

IP_RESOLVER = "speed.cloudflare.com"
PATH_RESOLVER = "/meta"
TIMEOUT = 5

def check(host, path, proxy):
    start_time = time.time()
    payload = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "User-Agent: Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.10240\r\n"
        "Connection: close\r\n\r\n"
    )

    ip = proxy.get("ip", host)
    port = int(proxy.get("port", 443))

    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((ip, port), timeout=TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as conn:
                conn.sendall(payload.encode())
                resp = b""
                while True:
                    data = conn.recv(4096)
                    if not data:
                        break
                    resp += data

                resp = resp.decode("utf-8", errors="ignore")
                headers, body = resp.split("\r\n\r\n", 1)
                end_time = time.time()
                connection_time = (end_time - start_time) * 1000

                try:
                    json_body = json.loads(body)
                    http_protocol = json_body.get("httpProtocol", "Unknown")
                    return json_body, http_protocol, connection_time
                except (json.JSONDecodeError, KeyError):
                    return {}, "Unknown", connection_time

    except (socket.timeout, socket.error, ssl.SSLError):
        return {}, "Unknown", 0

    return {}, "Unknown", 0

def clean_org_name(org_name):
    return re.sub(r'[^a-zA-Z0-9\s]', '', org_name) if org_name else org_name

def get_country_info(alpha_2):
    try:
        if alpha_2:
            country = pycountry.countries.get(alpha_2=alpha_2)
            if country:
                return country.name, getattr(country, 'flag', None)
        return "Unknown", None
    except Exception:
        return "Unknown", None

def process_proxy(ip, port):
    proxy_data = {"ip": ip, "port": port}

    ori, ori_protocol, ori_connection_time = check(IP_RESOLVER, PATH_RESOLVER, {})
    pxy, pxy_protocol, pxy_connection_time = check(IP_RESOLVER, PATH_RESOLVER, proxy_data)

    if ori and not ori.get("error") and pxy and not pxy.get("error") and ori.get("clientIp") != pxy.get("clientIp"):
        org_name = clean_org_name(pxy.get("asOrganization"))
        proxy_country_code = pxy.get("country") or "Unknown"
        proxy_asn = pxy.get("asn") or "Unknown"
        proxy_latitude = pxy.get("latitude") or "Unknown"
        proxy_longitude = pxy.get("longitude") or "Unknown"
        proxy_colo = pxy.get("colo") or "Unknown"
        proxy_country_name, proxy_country_flag = get_country_info(proxy_country_code)
        result_message = f"ProxyIP is Alive {ip}:{port}"
        return True, result_message, proxy_country_code, proxy_asn, proxy_country_name, proxy_country_flag, pxy_protocol, org_name, pxy_connection_time, proxy_latitude, proxy_longitude, proxy_colo
    else:
        dead_message = f"ProxyIP is Dead: {ip}:{port}"
        return False, dead_message, "Unknown", "Unknown", "Unknown", None, "Unknown", "Unknown", 0, "Unknown", "Unknown", "Unknown"

app = FastAPI()

@app.get("/api/v1/check")
async def check_proxy_url_endpoint(
    proxyip: str = Query(None, description="Proxy in format IP:PORT")
):
    if proxyip is None:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Parameter 'proxyip' must be provided in the URL.",
                "example": "/api/v1/check?proxyip=1.2.3.4:443 or /api/v1/check?proxyip=4.3.2.1"
            },
        )

    try:
        parts = proxyip.split(':')
        ip = parts[0]
        port = parts[1] if len(parts) > 1 else "443"
        
        if not ip:
            raise ValueError("IP address cannot be empty.")

    except (ValueError, IndexError):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid 'proxyip' format.",
                "expected_format": "IP:PORT"
            }
        )

    try:
        port_number = int(port)
        result = process_proxy(ip, port_number)
        is_alive, message, country_code, asn, country_name, country_flag, http_protocol, org_name, connection_time, latitude, longitude, colo = result

        if is_alive:
            response_data = {
                "ip": ip,
                "port": port_number,
                "proxyip": True,
                "asOrganization": org_name,
                "countryCode": country_code,
                "countryName": country_name,
                "countryFlag": country_flag,
                "asn": asn,
                "colo": colo,
                "httpProtocol": http_protocol,
                "ping": f"{round(connection_time)}",
                "latitude": latitude,
                "longitude": longitude,
                "message": message
            }
        else:
            response_data = {
                "ip": ip,
                "port": port_number,
                "proxyip": False,
                "asn": asn,
                "message": message
            }

        return response_data

    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Port must be a number."})
    except Exception as e:
        error_message = f"An internal server error occurred while processing the proxy {ip}:{port}: {e}"
        print(error_message)
        return JSONResponse(status_code=500, content={"error": error_message})
