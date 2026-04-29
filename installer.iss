[Setup]
AppId={{F3A2B1C4-7D8E-4F9A-B2C3-1D4E5F6A7B8C}
AppName=Instrument Tracker
AppVersion=2.3.1
AppPublisher=JD Messenger
AppPublisherURL=
DefaultDirName={autopf}\Instrument Tracker
DefaultGroupName=Instrument Tracker
OutputDir=installer_output
OutputBaseFilename=InstrumentTracker_Setup
SetupIconFile=icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayIcon={app}\Instrument Tracker.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
; All files from PyInstaller output folder
Source: "dist\Instrument Tracker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Instrument Tracker"; Filename: "{app}\Instrument Tracker.exe"
Name: "{group}\Uninstall Instrument Tracker"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Instrument Tracker"; Filename: "{app}\Instrument Tracker.exe"; Tasks: desktopicon

[Run]
; Pre-warm Windows Defender's DLL cache so first user launch is fast. Runs hidden, user never sees it.
Filename: "{app}\Instrument Tracker.exe"; Parameters: "--warmup"; StatusMsg: "Optimizing for first run (this may take a moment)…"; Flags: runhidden waituntilterminated
Filename: "{app}\Instrument Tracker.exe"; Description: "Launch Instrument Tracker"; Flags: nowait postinstall skipifsilent
