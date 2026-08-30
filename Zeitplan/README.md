# Beamten-Monitor Avatar – Zeitplan

Dieser Ordner ist die **Cloud-Quelle** für den Zeitplan des Beamten-Monitor Avatar.

Standard-Ordneradresse in der App:

```text
https://github.com/galgental9ps-png/VerwaltungsQuestBayern/tree/main/src/BeamtenMonitorAvatar/Zeitplan
```

Die App löst aus dieser Ordneradresse automatisch die Datei `zeitplan.json` auf.

---

## Betriebsarten

Im Einstellungsfenster unter **ZEITPLAN** gibt es drei Modi:

### Lokal

Verwendet:

```text
%LOCALAPPDATA%\BeamtenMonitorAvatar\Zeitplan\zeitplan.json
```

Der Zeitplan kann direkt im Einstellungsfenster angelegt, geändert und gespeichert werden.

### Cloud

Verwendet die in `settings.json` gespeicherte `ScheduleCloudSource`.

Standard:

```text
https://github.com/galgental9ps-png/VerwaltungsQuestBayern/tree/main/src/BeamtenMonitorAvatar/Zeitplan
```

Auch eine direkte `.json`-Adresse ist zulässig.

### Deaktiviert

Es werden keine zeitgesteuerten Auftritte ausgeführt. Manuelles Öffnen über Klingel oder Tray bleibt möglich.

---

## Struktur von zeitplan.json

```json
{
  "Version": 1,
  "Entries": [
    {
      "Id": "montag-0800",
      "Day": "Montag",
      "Time": "08:00",
      "Repeat": true,
      "Enabled": true
    }
  ]
}
```

### Felder

- `Version`: Formatversion des Zeitplans
- `Id`: eindeutige Kennung des Termins
- `Day`: Montag bis Sonntag
- `Time`: Uhrzeit im Format `HH:mm`
- `Repeat: true`: Termin wird wöchentlich wiederholt
- `Repeat: false`: Termin wird nach der ersten erfolgreichen Ausführung lokal als erledigt markiert
- `Enabled: false`: Termin wird ignoriert

Die App akzeptiert deutsche und englische Wochentagsnamen.

---

## Lokaler Laufzustand

Der Laufzustand für einmalige Termine wird getrennt gespeichert:

```text
%LOCALAPPDATA%\BeamtenMonitorAvatar\Zeitplan\state.json
```

Dadurch bleibt der Cloud-Zeitplan unverändert, während jeder Client lokal weiß, welche einmaligen Termine bereits ausgeführt wurden.

---

## Automatischer Auftritt

Ist ein Termin fällig und die App läuft:

1. Der Avatar öffnet sich automatisch.
2. Ein Klick auf die Klingel ist nicht erforderlich.
3. Der Auftritt erfolgt ohne Klingelton.
4. Die normale Avatar-Animation wird abgespielt.
5. Wird nichts angeklickt, greift die normale Zwei-Minuten-Inaktivitätslogik.
6. Danach zieht sich der Avatar automatisch zurück.
7. Wird eine echte Information geöffnet, bleibt sie zum Lesen sichtbar und der Auto-Rückzug pausiert.

---

## Zeitplan im Einstellungsfenster bearbeiten

Im Tab **ZEITPLAN** können mehrere Einträge gepflegt werden.

Pro Termin:

- Wochentag auswählen
- Uhrzeit eingeben
- `Wiederholen` aktivieren oder deaktivieren
- `TERMIN HINZUFÜGEN`

Verfügbare Aktionen:

- `AUSGEWÄHLTEN LÖSCHEN`
- `ZEITPLAN LADEN`
- `ZEITPLAN SPEICHERN`

`ZEITPLAN SPEICHERN` schreibt immer den lokalen Zeitplan nach:

```text
%LOCALAPPDATA%\BeamtenMonitorAvatar\Zeitplan\zeitplan.json
```

---

## Zusammenhang mit settings.json

Die Hauptkonfiguration liegt unter:

```text
%LOCALAPPDATA%\BeamtenMonitorAvatar\settings.json
```

Dort befinden sich unter anderem:

```json
{
  "ScheduleMode": "Disabled",
  "ScheduleCloudSource": "https://github.com/galgental9ps-png/VerwaltungsQuestBayern/tree/main/src/BeamtenMonitorAvatar/Zeitplan"
}
```

Erlaubte Werte für `ScheduleMode`:

```text
Disabled
Local
Cloud
```

---

## Technische Dateien

```text
src/BeamtenMonitorAvatar/
├─ MainWindow.Schedule.cs
├─ Models/
│  └─ ScheduleModels.cs
├─ Services/
│  └─ ScheduleService.cs
└─ Zeitplan/
   ├─ README.md
   └─ zeitplan.json
```

Die vollständige Projektdokumentation befindet sich unter:

```text
docs/BeamtenMonitorAvatar_Dokumentation.md
```
