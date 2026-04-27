[Setup]
AppName=WITTGrp Download Manager
AppVersion=1.0.0
AppPublisher=WITTGrp
AppSupportURL=https://github.com/sharmarajeshkr/Downloadmanager
DefaultDirName={autopf}\WITTGrp
DefaultGroupName=WITTGrp
UninstallDisplayIcon={app}\WITTGrp.exe
Compression=lzma2
SolidCompression=yes
OutputDir=dist
OutputBaseFilename=WITTGrp_Setup
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "dist\WITTGrp.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\WITTGrp Download Manager"; Filename: "{app}\WITTGrp.exe"
Name: "{autodesktop}\WITTGrp Download Manager"; Filename: "{app}\WITTGrp.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"
