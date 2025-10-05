#!/usr/bin/env python3
"""
Script de vérification de la configuration des credentials
NASA Space Apps Challenge 2025
"""

import json
import os
import sys
from pathlib import Path


def print_header(text):
    """Affiche un en-tête formaté"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)


def print_status(check_name, status, message=""):
    """Affiche le statut d'une vérification"""
    symbols = {
        'ok': '✅',
        'warning': '⚠️',
        'error': '❌',
        'info': 'ℹ️'
    }
    symbol = symbols.get(status, '•')
    print(f"{symbol} {check_name}: {message}")


def check_file_exists(filepath, required=True):
    """Vérifie l'existence d'un fichier"""
    path = Path(filepath)
    if path.exists():
        return True, f"Trouvé ({path.stat().st_size} octets)"
    else:
        if required:
            return False, f"MANQUANT - Requis"
        else:
            return None, "Optionnel - Non trouvé"


def check_gitignore():
    """Vérifie que .gitignore contient les entrées nécessaires"""
    print_header("VÉRIFICATION .gitignore")
    
    if not Path('.gitignore').exists():
        print_status(".gitignore", "error", "Fichier .gitignore manquant!")
        return False
    
    with open('.gitignore', 'r') as f:
        content = f.read()
    
    required_entries = [
        'credentials.json',
        'token.pickle',
        '.env'
    ]
    
    all_found = True
    for entry in required_entries:
        if entry in content:
            print_status(entry, "ok", "Présent dans .gitignore")
        else:
            print_status(entry, "error", "ABSENT de .gitignore")
            all_found = False
    
    return all_found


def check_credentials_file():
    """Vérifie le fichier credentials.json"""
    print_header("VÉRIFICATION credentials.json")
    
    exists, msg = check_file_exists('credentials.json')
    
    if not exists:
        print_status("credentials.json", "error", msg)
        print("\n💡 Pour créer le fichier:")
        print("   cp credentials.json.example credentials.json")
        print("   # Puis éditer avec vos vrais identifiants")
        return False
    
    print_status("credentials.json", "ok", msg)
    
    # Vérifier le contenu
    try:
        with open('credentials.json', 'r') as f:
            creds = json.load(f)
        
        # Vérifier Copernicus
        if 'copernicus' in creds:
            print_status("Section copernicus", "ok", "Présente")
            
            if 'username' in creds['copernicus']:
                username = creds['copernicus']['username']
                if username and not username.startswith('VOTRE_'):
                    print_status("  └─ username", "ok", f"Configuré ({username})")
                else:
                    print_status("  └─ username", "warning", "Utilise encore le template")
            else:
                print_status("  └─ username", "error", "MANQUANT")
            
            if 'password' in creds['copernicus']:
                password = creds['copernicus']['password']
                if password and not password.startswith('VOTRE_'):
                    # Ne pas afficher le mot de passe
                    print_status("  └─ password", "ok", f"Configuré ({len(password)} caractères)")
                else:
                    print_status("  └─ password", "warning", "Utilise encore le template")
            else:
                print_status("  └─ password", "error", "MANQUANT")
        else:
            print_status("Section copernicus", "error", "MANQUANTE")
        
        # Vérifier Google Drive (optionnel)
        if 'installed' in creds:
            print_status("Section Google Drive", "ok", "Présente (optionnel)")
            
            if 'client_id' in creds['installed']:
                client_id = creds['installed']['client_id']
                if client_id and not client_id.startswith('VOTRE_'):
                    print_status("  └─ client_id", "ok", "Configuré")
                else:
                    print_status("  └─ client_id", "info", "Template - configurer si besoin")
        else:
            print_status("Section Google Drive", "info", "Absente (optionnel)")
        
        return True
        
    except json.JSONDecodeError as e:
        print_status("Format JSON", "error", f"Invalide - {e}")
        return False
    except Exception as e:
        print_status("Lecture", "error", str(e))
        return False


def check_template_exists():
    """Vérifie que le template existe"""
    print_header("VÉRIFICATION credentials.json.example")
    
    exists, msg = check_file_exists('credentials.json.example', required=False)
    
    if exists:
        print_status("credentials.json.example", "ok", msg)
        return True
    else:
        print_status("credentials.json.example", "warning", "Template manquant (recommandé pour les autres utilisateurs)")
        return False


def check_no_hardcoded_credentials():
    """Vérifie qu'il n'y a pas de credentials en dur dans le code"""
    print_header("VÉRIFICATION Credentials en Dur")
    
    suspicious_patterns = [
        'password = "',
        'password="',
        "password = '",
        "password='",
        '@gmail.com"',
        '@outlook.com"',
        'api_key = "',
        'token = "'
    ]
    
    python_files = Path('.').rglob('*.py')
    issues_found = False
    
    for py_file in python_files:
        # Ignorer les fichiers de vérification et exemples
        if 'check_credentials' in str(py_file) or 'example' in str(py_file):
            continue
        
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                line_num = 0
                
                for line in content.split('\n'):
                    line_num += 1
                    for pattern in suspicious_patterns:
                        if pattern in line and 'load_credentials' not in line:
                            print_status(
                                f"{py_file}:{line_num}",
                                "warning",
                                f"Possiblement sensible: {line.strip()[:60]}..."
                            )
                            issues_found = True
        except Exception as e:
            pass
    
    if not issues_found:
        print_status("Scan du code", "ok", "Aucun credential en dur détecté")
    
    return not issues_found


def check_git_status():
    """Vérifie que credentials.json n'est pas tracké par Git"""
    print_header("VÉRIFICATION Git Status")
    
    try:
        import subprocess
        
        # Vérifier si on est dans un repo Git
        result = subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print_status("Repository Git", "info", "Pas un repository Git")
            return True
        
        # Vérifier si credentials.json est tracké
        result = subprocess.run(
            ['git', 'ls-files', 'credentials.json'],
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            print_status(
                "credentials.json",
                "error",
                "TRACKÉ PAR GIT - Danger de fuite!"
            )
            print("\n💡 Pour corriger:")
            print("   git rm --cached credentials.json")
            print("   git commit -m 'Remove credentials.json from tracking'")
            return False
        else:
            print_status("credentials.json", "ok", "Non tracké par Git")
        
        # Vérifier si token.pickle est tracké
        result = subprocess.run(
            ['git', 'ls-files', 'token.pickle'],
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            print_status(
                "token.pickle",
                "error",
                "TRACKÉ PAR GIT - Danger de fuite!"
            )
            return False
        else:
            print_status("token.pickle", "ok", "Non tracké par Git")
        
        return True
        
    except FileNotFoundError:
        print_status("Git", "info", "Git non installé")
        return True


def test_api_connection():
    """Teste la connexion à l'API Copernicus"""
    print_header("TEST Connexion API Copernicus")
    
    try:
        # Importer la fonction de chargement
        sys.path.insert(0, str(Path(__file__).parent / 'src' / 'api'))
        from sentinelAPI import load_credentials, get_copernicus_token
        
        creds = load_credentials('credentials.json')
        username = creds['copernicus']['username']
        password = creds['copernicus']['password']
        
        print_status("Chargement credentials", "ok", "Succès")
        
        print("   Tentative de connexion...", end='', flush=True)
        token = get_copernicus_token(username, password)
        print(" ✅ Succès!")
        
        print_status("Authentification", "ok", f"Token obtenu ({len(token)} caractères)")
        return True
        
    except FileNotFoundError:
        print_status("Test API", "warning", "Fichier sentinelAPI.py non trouvé")
        return False
    except Exception as e:
        print_status("Authentification", "error", str(e))
        print("\n💡 Vérifiez:")
        print("   1. Username et password sont corrects")
        print("   2. Connexion Internet active")
        print("   3. Compte Copernicus activé")
        return False


def print_summary(checks):
    """Affiche un résumé des vérifications"""
    print_header("RÉSUMÉ")
    
    total = len(checks)
    passed = sum(1 for check in checks.values() if check)
    
    if passed == total:
        print(f"✅ Toutes les vérifications sont passées ({passed}/{total})")
        print("\n🚀 Vous pouvez utiliser le projet en toute sécurité!")
    else:
        failed = total - passed
        print(f"⚠️  {failed} vérification(s) échouée(s) sur {total}")
        print("\n💡 Consultez SECURITY.md pour plus d'informations")
    
    print("\n📋 Détails:")
    for check_name, status in checks.items():
        symbol = "✅" if status else "❌"
        print(f"   {symbol} {check_name}")


def main():
    """Fonction principale"""
    print("\n" + "🔒 " + "="*68)
    print("   VÉRIFICATION DE LA CONFIGURATION DE SÉCURITÉ")
    print("   NASA Space Apps Challenge 2025")
    print("="*70)
    
    checks = {}
    
    # Exécuter toutes les vérifications
    checks['Fichier .gitignore'] = check_gitignore()
    checks['Fichier credentials.json'] = check_credentials_file()
    checks['Template credentials.json.example'] = check_template_exists()
    checks['Pas de credentials en dur'] = check_no_hardcoded_credentials()
    checks['Git tracking'] = check_git_status()
    checks['Connexion API'] = test_api_connection()
    
    # Résumé
    print_summary(checks)
    
    # Code de sortie
    if all(checks.values()):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()