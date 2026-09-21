# Dépannage

Les problèmes les plus courants et leurs solutions.

## Erreur « externally-managed-environment »

**Symptôme** - `pip install -r requirements.txt` affiche :

```
error: externally-managed-environment
```

**Cause** - Raspberry Pi OS (et Debian récent) empêche volontairement
d'installer des paquets Python directement sur le système.

**Solution** - utilise un environnement virtuel :

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Puis lance le serveur avec ce venv (ou laisse ESP32-Lab le détecter tout seul,
voir ci-dessous).

## « No module named esptool »

**Symptôme** - la lecture des partitions ou le scan échoue avec
`/usr/bin/python: No module named esptool`.

**Cause** - le serveur a été lancé avec un Python (souvent le Python système)
qui ne dispose pas d'esptool.

**Solutions** :

1. Lance le serveur avec le Python du `.venv` :
   ```bash
   PYTHONPATH=src .venv/bin/python -m web.server
   ```
2. Ou vérifie qu'esptool est bien installé dans le `.venv` :
   ```bash
   .venv/bin/pip install esptool
   ```

> ESP32-Lab tente de détecter automatiquement l'esptool du `.venv` même lancé
> avec le Python système. Si l'erreur persiste, c'est que le `.venv` n'existe
> pas ou n'a pas esptool : refais l'étape 2.

## Aucun port détecté

**Symptôme** - le menu affiche « Aucun port USB détecté ».

**À vérifier** :

1. Le câble USB transmet-il les **données** (certains câbles ne font que la
   charge) ? Essaie un autre câble.
2. La carte apparaît-elle au système ?
   ```bash
   ls /dev/ttyACM* /dev/ttyUSB*      # Linux
   ```
3. Clique sur **Actualiser les ports** dans l'interface.
4. **Droits d'accès** (Linux) : ajoute ton utilisateur au groupe `dialout`,
   puis reconnecte-toi :
   ```bash
   sudo usermod -a -G dialout $USER
   ```

## Le port est occupé / busy

**Symptôme** - `Could not open ... the port is busy`.

**Cause** - un autre programme utilise déjà le port (moniteur série, autre
instance, IDE…).

**Solution** - ferme l'autre programme (moniteur série Arduino/PlatformIO,
`screen`, `minicom`, etc.) puis réessaie.

## La page est cassée / sans style après une mise à jour

**Symptôme** - après avoir modifié le code, la page s'affiche sans style ou une
fonction ne marche pas.

**Causes possibles** :

- **Cache du navigateur** : force le rechargement avec `Ctrl+F5`.
- **Serveur non redémarré** : si tu as modifié un fichier `.py` (surtout
  `server.py`), le serveur garde l'ancien code en mémoire. **Redémarre-le**
  (`Ctrl+C` puis relance la commande). Les fichiers HTML/CSS/JS, eux, sont
  relus à chaque requête : un simple rechargement suffit.

## L'analyse NVS affiche « (non stocké en base) »

**Ce n'est pas un bug, c'est voulu.** Pour ne jamais conserver de secret (ni de
copie résiduelle de mot de passe/SSID), ESP32-Lab n'enregistre **aucun octet
brut NVS** en base : seule la structure est gardée. Donc, quand tu **charges
depuis la base**, les valeurs décodées apparaissent « (non stocké en base) » et
les mots de passe « Présent (masqué) ».

Pour voir les valeurs décodées (SSID, canal…), fais une **lecture live** : bouton
**« Analyser la NVS de la carte »** (la carte doit être branchée). Les autres
sections (eFuses, SFDP, partitions) se réaffichent, elles, entièrement depuis la
base avec « Charger depuis la base ».

## L'onglet NVS reste vide pour une carte

« Charger l'analyse NVS » cherche la dernière analyse **de cette carte** en base
(par sa MAC). Si aucune n'existe et qu'un port est sélectionné, l'analyse est
**déclenchée automatiquement**. Sinon, branche la carte, sélectionne son port
(onglet Général) puis clique sur « Analyser la NVS de la carte ».

## Vérifier que le serveur répond

```bash
curl http://localhost:8765/api/health
```

Réponse attendue :

```json
{ "status": "ok", "service": "ESP32-Lab", "version": "0.9.0" }
```

## Toujours bloqué ?

Note le message d'erreur exact (terminal **et** console du navigateur, touche
`F12`) : c'est le point de départ pour diagnostiquer.
