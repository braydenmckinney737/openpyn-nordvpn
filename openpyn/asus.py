import logging
import os
import subprocess

import verboselogs

from openpyn import api
from openpyn import credentials_file_path
from openpyn import ovpn_folder
from openpyn import sudo_user
from openpyn.converter import T_CLIENT
from openpyn.converter import Converter

verboselogs.install()
logger = logging.getLogger(__package__)


def run(server, client, options=None, rgw=None, comp=None, adns=None, tcp=False, test=False, debug=False):
    country_name = api.get_country_name(server[:2])

    with open(credentials_file_path, "r") as f:
        lines = f.read().splitlines()

    port = "udp"
    port_name = "1194"
    protocol_name = "udp"
    folder = "/ovpn_udp/"
    if tcp:
        port = "tcp"
        port_name = "443"
        protocol_name = "tcp-client"
        folder = "/ovpn_tcp/"

    vpn_config_file = server + ".nordvpn.com." + port + ".ovpn"

    certs_folder = "/jffs/openvpn/"

    if not os.path.exists(certs_folder):
        os.mkdir(certs_folder, 0o700)
        os.chmod(certs_folder, 0o700)

    c = Converter(debug)
    c.set_username(lines[0])
    c.set_password(lines[1])
    c.set_description("Client" + " " + country_name)
    c.set_port(port_name)
    c.set_protocol(protocol_name)

    c.set_name(server)
    c.set_source_folder(ovpn_folder + folder)
    c.set_certs_folder(certs_folder)

    c.set_accept_dns_configuration(adns)
    c.set_compression(comp)
    c.set_redirect_gateway(rgw)
    c.set_client(client)

    if options:
        c.set_openvpn_options("\n".join(filter(None, options.split("--"))) + "\n")

    extracted_info = c.extract_information(vpn_config_file)
    if not test:
        c.write_certificates(client)

    c.pprint(extracted_info)

    # 'vpn_client_unit'
    key = ""
    value = ""
    unit = ""
    service = "client"

    for key, value in extracted_info.items():
        write(c, key, value, unit, service, test)

    extracted_info = dict(extracted_info)
    if T_CLIENT in extracted_info:
        del extracted_info[T_CLIENT]

    c.pprint(extracted_info)

    # 'vpn_client_unit$'
    key = ""
    value = ""
    unit = client
    service = "client"

    for key, value in extracted_info.items():
        write(c, key, value, unit, service, test)

    # 'vpn_upload_unit'
    key = T_CLIENT
    value = client
    unit = ""
    service = "upload"

    write(c, key, value, unit, service, test)


def write(c, key, value, unit, service, test=False):
    argument1 = "vpn" + "_" + service + unit + "_" + key
    argument2 = argument1 + "=" + value
    try:
        c.pprint("/bin/nvram" + " " + "get" + " " + argument1)
        if not test:
            current = subprocess.run(["/bin/nvram", "get", argument1], check=True, stdout=subprocess.PIPE).stdout
            if current.decode("utf-8").strip() == value:
                return
        c.pprint("/bin/nvram" + " " + "set" + " " + argument2)
        if not test:
            subprocess.run(["sudo", "-u", sudo_user, "/bin/nvram", "set", argument2], check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(e.output)
