Beamten-Monitor Avatar – verbindlicher Aufbau eines Asset-Sets

STANDARD-GITHUB-QUELLE
https://github.com/galgental9ps-png/beamten-avatar-asset/tree/main/BeamtenMonitorAvatar

MASCHINENLESBARE SPEZIFIKATION
Die verbindlichen Größen, Dateipfade und Prüfregeln stehen in:
BeamtenMonitorAvatar/AssetSetSpec.json

ORDNERSTRUKTUR
Jeder Ordner Assets, Assets 1, Assets 2 usw. verwendet exakt diese Struktur:

Avatar/Idle.png
Avatar/Actions.png
MonitorScene/MonitorScene.png
Klingel/MonitorBell.png
Sprüche/Abschiedsspruch.json

Assets/Sprüche/Fallback.json enthält die geprüften Standardsprüche als Reserve und bleibt ausschließlich im Basis-Set Assets.

VERBINDLICHE PNG-GRÖSSEN
Idle.png: 1024 x 1536 Pixel
Actions.png: 1536 x 1024 Pixel, exaktes 4x2-Sprite-Sheet
MonitorScene.png: 1672 x 941 Pixel
MonitorBell.png: 1254 x 1254 Pixel

Alle PNGs benötigen einen echten Alphakanal und transparente Flächen. Figuren und Motive dürfen nicht angeschnitten sein.

ACTIONS-SPRITE-SHEET
Obere Reihe: Idle, Gehen 1, Gehen 2, Rennen
Untere Reihe: Jubelsprung, Sprung/Landung, Präsentieren, Lesen/Betrachten

Alle oberen Bewegungsframes schauen nach rechts. Gehen 1 und Gehen 2 unterscheiden sich nur durch Beinstellung und Armschwung. Die App spiegelt das komplette Sprite beim Zurücklaufen selbst.

AUTOMATISCHER UPLOAD
Neue Sets werden als Geschwisterordner BeamtenMonitorAvatar/Assets N angelegt. Die Automatik liest zuerst AssetSetSpec.json und die vier Referenz-PNGs aus BeamtenMonitorAvatar/Assets. Vorhandene Sets dürfen niemals überschrieben werden.

Ein Set gilt erst als erfolgreich, wenn alle vier PNGs und die Spruch-JSON in einem Commit auf main hochgeladen und anschließend direkt von GitHub erneut geprüft wurden.
