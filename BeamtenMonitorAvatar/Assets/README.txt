Beamten-Monitor Avatar – Aufbau eines Asset-Sets

Jeder Ordner Assets, Assets 1, Assets 2 usw. verwendet dieselbe Struktur:

Avatar\Idle.png
Avatar\Actions.png
MonitorScene\MonitorScene.png
Klingel\MonitorBell.png
Sprüche\Abschiedsspruch.json

Idle.png ist das einzelne Präsentationsbild.
Actions.png ist das Sprite-Sheet für Lauf-, Sprung- und Aktionsanimationen.
MonitorScene.png enthält Hauseingang, Boden und Umgebungsbild.
MonitorBell.png ist die Desktop- und Tray-Klingel.
Abschiedsspruch.json enthält genau einen zum Thema des Sets passenden humorvollen Abschiedsspruch.
Assets\Sprüche\Fallback.json enthält die bisherigen geprüften Standardsprüche als Reserve.

Weitere Sets werden als Geschwisterordner neben Assets angelegt, zum Beispiel:
Assets 1
Assets 2
Assets Augsburg

Die App erkennt alle Ordner automatisch, deren Name mit Assets beginnt.

Standard-GitHub-Quelle für die App:
https://github.com/galgental9ps-png/VerwaltungsQuestBayern/tree/main/src/BeamtenMonitorAvatar

Diese Adresse ist in den App-Einstellungen als Standard eingetragen.
