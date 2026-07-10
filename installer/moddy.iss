; Moddy Launcher – Inno Setup Script
; Wymaga: Inno Setup 6.x  (https://jrsoftware.org/isinfo.php)
; Budowanie: ISCC.exe installer\moddy.iss

#define AppName      "Moddy Launcher"
#define AppVersion   "1.0.0-beta"
#define AppPublisher "Moddy"
#define AppURL       "https://moddy.app"
#define AppExeName   "Moddy.exe"
#define AppId        "{{8F3A2C1D-4B5E-4F6A-9C8D-1E2F3A4B5C6D}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} Beta 1.0
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/support
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\Moddy
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile=license.txt
OutputDir=..\dist
OutputBaseFilename=Moddy_Beta_1.0_Setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName} Beta 1.0
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardResizable=no
WizardSizePercent=120
DisableProgramGroupPage=no
PrivilegesRequiredOverridesAllowed=dialog
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
CloseApplicationsFilter=Moddy.exe
RestartApplications=no
ShowLanguageDialog=no
LanguageDetectionMethod=none
DisableWelcomePage=no
DisableReadyMemo=no

; Kolory / styl (Inno Setup 6.3+)
WizardImageFile=compiler:WizModernImage-IS.bmp
WizardSmallImageFile=compiler:WizModernSmallImage-IS.bmp

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"

[Tasks]
Name: "desktopicon"; Description: "Utwórz skrót na {cm:DesktopName}"; GroupDescription: "Skróty:"; Flags: unchecked
Name: "autostart";   Description: "Uruchamiaj Moddy automatycznie z Windows"; GroupDescription: "Opcje:"; Flags: unchecked

[Files]
; Jeden plik EXE (PyInstaller --onefile)
Source: "..\dist\Moddy.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}";         Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\Odinstaluj Moddy";  Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
; Wpis w Panel sterowania → Programy (dla instalacji user-level)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1"; \
  ValueType: string; ValueName: "DisplayName";         ValueData: "{#AppName} Beta 1.0"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1"; \
  ValueType: string; ValueName: "DisplayVersion";      ValueData: "{#AppVersion}"
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1"; \
  ValueType: string; ValueName: "Publisher";           ValueData: "{#AppPublisher}"
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1"; \
  ValueType: string; ValueName: "URLInfoAbout";        ValueData: "{#AppURL}"

; Autostart (tylko jeśli zaznaczono)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#AppExeName}"""; \
  Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#AppExeName}"; \
  Description: "Uruchom {#AppName}"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; Zamknij Moddy przed odinstalowaniem
Filename: "taskkill.exe"; Parameters: "/F /IM {#AppExeName}"; Flags: runhidden; RunOnceId: "KillModdy"

[UninstallDelete]
; Usuń logi i cache po odinstalowaniu (dane użytkownika w APPDATA zostają)
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\__pycache__"

[Messages]
WelcomeLabel1=Witaj w instalatorze [name]
WelcomeLabel2=Instalator przeprowadzi Cię przez instalację [name/ver] na Twoim komputerze.%n%nModdy to nowoczesny launcher Minecraft z obsługą modów, modpacków i wbudowanym AI generatorem.%n%nZalecane jest zamknięcie wszystkich innych aplikacji przed kontynuowaniem.
FinishedHeadingLabel=Instalacja [name] zakończona
FinishedLabel=Moddy Beta 1.0 został pomyślnie zainstalowany.%n%nMożesz teraz uruchomić launcher klikając przycisk poniżej.
