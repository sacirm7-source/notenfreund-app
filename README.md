# Notenfreund – Python-Version für den Handytest

Diese Version läuft als lokale Web-App: Python (Flask) verwaltet Stücke und Dateien; die Oberfläche öffnet sich im Browser. Kein Java und kein Android-Build sind nötig.

## Funktionen

- PDF-, MuseScore-, MusicXML- und MIDI-Dateien importieren
- Lokale Bibliothek mit Suche und Statusfilter
- Status setzen, Titel und Komponist ändern
- Stück für heute als geübt markieren
- Zufälliges Stück aus „Neu“ und „In Übung“ auswählen
- Eintrag und dazugehörige Datei löschen
- PDF im Browser öffnen

## Start unter Windows

1. Installiere Python 3 von https://www.python.org/downloads/windows/ und aktiviere im Installer „Add python.exe to PATH“.
2. Öffne PowerShell im Projektordner.
3. Installiere Flask: `py -m pip install -r requirements.txt`
4. Starte die App: `py app.py`
5. Öffne auf dem PC `http://127.0.0.1:5000`.

## Android-Handy verbinden

PC und Handy müssen im selben privaten WLAN sein. Ermittle auf dem PC mit `ipconfig` die IPv4-Adresse des WLAN-Adapters. Öffne am Handy `http://DEINE-PC-IP:5000` (ersetze den Platzhalter, zum Beispiel durch `http://192.168.1.25:5000`). Falls Windows fragt, erlaube den Zugriff nur in privaten Netzwerken. Die App läuft, solange das Terminalfenster mit `py app.py` geöffnet bleibt.

Alle Daten bleiben im Projektordner: `notenfreund.db` und `uploads/`. Erstelle eine Sicherungskopie des Ordners, bevor du ihn verschiebst oder löschst. Diese Web-Version wird nicht als APK installiert.

## Unterstützte Vorschau

PDF kann im Browser geöffnet werden. MuseScore-, MusicXML- und MIDI-Dateien werden lokal gespeichert und katalogisiert, haben in diesem MVP aber noch keine eingebettete Vorschau.
