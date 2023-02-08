import subprocess
import sys
import logging
import time
import os
import signal
from dataclasses import dataclass

@dataclass(frozen=True)
class Keys:
    private : str
    public : str

_log_format = f"%(name)s [%(asctime)s] %(message)s"

def get_logger(name : str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(logging.Formatter(_log_format))
    logger.addHandler(stream_handler)
    return logger

logger = get_logger("YGK")

def generate_keys(genkeys : str, timeout : int) -> Keys:
    logger.info(f"start generating keys with timeout {timeout} seconds")
    priv : str = ""
    pub : str = ""
    commands = f"{genkeys}"
    process = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
    time.sleep(timeout)
    poll = process.poll()
    if (poll is not None):
        logger.warning("genkeys run error")
        return Keys(private=priv, public=pub)
    os.killpg(process.pid, signal.SIGTERM)
    output_str = process.communicate()[0].decode("utf-8")
    priv_label = "Priv: "
    pub_label = "Pub: "
    priv_pos_start = output_str.rfind(priv_label)
    if (priv_pos_start == -1):
        logger.warning("cant find private key start")
        return Keys(private=priv, public=pub)
    priv_pos_end = output_str.find("\n", priv_pos_start)
    if (priv_pos_end == -1):
        logger.warning("cant find private key end")
        return Keys(private=priv, public=pub)
    pub_pos_start = output_str.rfind(pub_label)
    if (pub_pos_start == -1):
        logger.warning("cant find public key start")
        return Keys(private=priv, public=pub)
    pub_pos_end = output_str.find("\n", pub_pos_start)
    if (pub_pos_end == -1):
        logger.warning("cant find public key end")
        return Keys(private=priv, public=pub)
    priv = output_str[priv_pos_start+len(priv_label):priv_pos_end]
    pub = output_str[pub_pos_start+len(pub_label):pub_pos_end]
    return Keys(private=priv, public=pub)

def keys_to_config(keys : Keys, yggdrasil_conf_filename : str) -> None:
    with open(yggdrasil_conf_filename, "r") as file:
        contents = file.readlines()

    new_contents : list[str] = []
    public_saved = False
    private_saved = False
    for line in contents:
        if (line.find("PublicKey:") != -1):
            new_contents.append(f"  PublicKey: {keys.public}\n")
            public_saved = True
        elif (line.find("PrivateKey:") != -1):
            new_contents.append(f"  PrivateKey: {keys.private}\n")
            private_saved = True
        else:
            new_contents.append(line)
    if (not public_saved):
        new_contents.append(f"  PublicKey: {keys.public}\n")
    if (not private_saved):
        new_contents.append(f"  PrivateKey: {keys.private}\n")

    with open(yggdrasil_conf_filename, "w") as file:
        new_content = "".join(new_contents)
        file.write(new_content)
    return

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description='Generate yggdrasil high address')
    parser.add_argument('--genkeys', dest='genkeys', metavar='GENKEYS', \
        type=str, default="genkeys", help='Location of genkeys program')
    parser.add_argument('--timeout', dest='timeout', metavar='TIMEOUT', \
        type=int, default=60, help='Time to generate keys in seconds')
    parser.add_argument('--yggdrasil-conf', dest='yggdrasil_conf', metavar='YGGDRASIL_CONF', \
        type=str, default="", help='Save generated keys to existing yggdrasil configuration file')
    parser.add_argument("-v", dest='verbose', help="Print extra logs",
        action="store_true")
    parser.add_argument("--environment", dest='environment', help="Use environment values YGGDRASIL_PUBLIC_KEY and YGGDRASIL_PRIVATE_KEY if set",
        action="store_true")
                    
    args = parser.parse_args()
    if (args.verbose):
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if (args.environment):
        env_pub = os.environ.get("YGGDRASIL_PUBLIC_KEY")
        env_priv = os.environ.get("YGGDRASIL_PUBLIC_KEY")
        if ((env_pub) and (env_priv)):
            keys = Keys(env_priv, env_pub)
            logger.info("keys got from environment")
            logger.debug(f"private: {keys.private}")
            logger.debug(f"public:  {keys.public}")
            if (args.yggdrasil_conf != ""):
                keys_to_config(keys, args.yggdrasil_conf)
            sys.exit(0)

    keys = generate_keys(args.genkeys, args.timeout)
    if ((keys.private != "") and (keys.public != "")):
        logger.info("keys generated successfuly")
        logger.debug(f"private: {keys.private}")
        logger.debug(f"public:  {keys.public}")
        if (args.yggdrasil_conf != ""):
            keys_to_config(keys, args.yggdrasil_conf)
    else:
        logger.warning("no keys generated")
        sys.exit(1)
    sys.exit(0)

if __name__ == '__main__':
    main()