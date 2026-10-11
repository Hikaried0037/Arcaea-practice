param(
 [switch]$TestOnly,
 [string]$PackageName='moe.inf.arc.practice',
 [string]$SourceApk=(Join-Path (Split-Path $PSScriptRoot) 'Arcaea Infinity_7.0.1f.apk\Arcaea Infinity_7.0.1f.apk'),
 [string]$AndroidSdk=$env:ANDROID_HOME,
 [string]$JavaHome=$env:JAVA_HOME,
 [string]$ApktoolJar=(Join-Path (Split-Path $PSScriptRoot) 'tools\apktool_3.0.3.jar'),
 [string]$Python='python',
 [string]$NdkVersion='29.0.14206865',
 [string]$BuildToolsVersion='35.0.0',
 [string]$AndroidPlatform='android-35',
 [string]$OutputDir=(Join-Path (Split-Path $PSScriptRoot) 'output'),
 [string]$KeyStore=(Join-Path $PSScriptRoot 'build\practice.p12'),
 [string]$KeyAlias='practice',
 [string]$KeyStorePasswordFile=(Join-Path $PSScriptRoot 'build\.keystore-password'),
 [switch]$ValidateOnly
)
$ErrorActionPreference='Continue'
if($PackageName -notmatch '^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$' -or $PackageName.Length -gt 127){throw 'Invalid Android package name'}
if(-not $AndroidSdk){$AndroidSdk=$env:ANDROID_SDK_ROOT}
if(-not $AndroidSdk){throw 'Set ANDROID_HOME or pass -AndroidSdk'}
if(-not $JavaHome){throw 'Set JAVA_HOME or pass -JavaHome'}
$sdk=[IO.Path]::GetFullPath($AndroidSdk)
$ndk=Join-Path $sdk "ndk\$NdkVersion\toolchains\llvm\prebuilt\windows-x86_64\bin"
$bt=Join-Path $sdk "build-tools\$BuildToolsVersion"
$java=Join-Path ([IO.Path]::GetFullPath($JavaHome)) 'bin'
$build=Join-Path $PSScriptRoot 'build'
$decoded=Join-Path $build 'decoded'
$source=[IO.Path]::GetFullPath($SourceApk)
$ApktoolJar=[IO.Path]::GetFullPath($ApktoolJar)
$OutputDir=[IO.Path]::GetFullPath($OutputDir)
$KeyStore=[IO.Path]::GetFullPath($KeyStore)
$KeyStorePasswordFile=[IO.Path]::GetFullPath($KeyStorePasswordFile)
$androidJar=Join-Path $sdk "platforms\$AndroidPlatform\android.jar"
$required=@($source,$ApktoolJar,$androidJar,"$ndk\clang++.exe","$java\java.exe","$java\javac.exe","$java\keytool.exe","$bt\d8.bat","$bt\zipalign.exe","$bt\apksigner.bat")
foreach($path in $required){if(-not(Test-Path -LiteralPath $path -PathType Leaf)){throw "Required file missing: $path"}}
if(-not(Get-Command $Python -ErrorAction SilentlyContinue)){throw "Python command not found: $Python"}
function CheckExit {if($LASTEXITCODE -ne 0){throw "Build tool failed: $LASTEXITCODE"}}
& $Python "$PSScriptRoot\verify_profile.py" $source
CheckExit
if($ValidateOnly){Write-Output 'Build inputs and native profile validated';return}
New-Item -ItemType Directory -Force "$build\classes","$build\dex",$OutputDir | Out-Null
# Always decode the specified input; never reuse an unrelated APK's smali.
& "$java\java.exe" -jar $ApktoolJar d -f --no-assets -r -o $decoded $source
CheckExit
& "$ndk\clang++.exe" --target=aarch64-linux-android24 -shared -fPIC -O2 -std=c++17 -static-libstdc++ '-Wl,-z,max-page-size=16384' "$PSScriptRoot\native\practice.cpp" -llog -ldl -o "$build\libarcpractice.so"
CheckExit
& "$java\javac.exe" -encoding UTF-8 -source 8 -target 8 -classpath $androidJar -d "$build\classes" "$PSScriptRoot\java\moe\practice\PracticeOverlay.java"
CheckExit
$classFiles=Get-ChildItem "$build\classes" -Recurse -Filter '*.class' | ForEach-Object {$_.FullName}
& "$bt\d8.bat" --min-api 24 --lib $androidJar --output "$build\dex" $classFiles
CheckExit
$smali="$decoded\smali_classes2\low\moe\AppActivity.smali"
$content=[IO.File]::ReadAllText($smali)
$providerPattern='(?m)(    const-string v2, )"[^"]+\.provider"'
if([regex]::Matches($content,$providerPattern).Count -ne 1){throw 'Share provider injection point missing'}
$content=[regex]::Replace($content,$providerPattern,'$1"'+$PackageName+'.provider"')
if(-not $content.Contains('Lmoe/practice/PracticeOverlay;->attach')){
 $needle='    invoke-static {p0}, Llow/moe/AppActivity;->protect(Landroid/content/Context;)V'
 if(-not $content.Contains($needle)){throw 'Activity injection point missing'}
 $content=$content.Replace($needle,$needle+"`n`n    invoke-static {p0}, Lmoe/practice/PracticeOverlay;->attach(Landroid/app/Activity;)V")
}
[IO.File]::WriteAllText($smali,$content,[Text.UTF8Encoding]::new($false))
$buildConfig="$decoded\smali_classes2\moe\low\arcdev\BuildConfig.smali"
$buildConfigContent=[IO.File]::ReadAllText($buildConfig)
$buildConfigContent=[regex]::Replace($buildConfigContent,'(\.field public static final APPLICATION_ID:Ljava/lang/String; = )"[^"]+"','$1"'+$PackageName+'"')
[IO.File]::WriteAllText($buildConfig,$buildConfigContent,[Text.UTF8Encoding]::new($false))
$renderer="$decoded\smali_classes2\org\cocos2dx\lib\Cocos2dxRenderer.smali"
$rendererContent=[IO.File]::ReadAllText($renderer)
if(-not $rendererContent.Contains('Lmoe/practice/PracticeOverlay;->frame')){
 $renderNeedle='    invoke-static {}, Lorg/cocos2dx/lib/Cocos2dxRenderer;->nativeRender()V'
 if(-not $rendererContent.Contains($renderNeedle)){throw 'Renderer injection point missing'}
 $rendererContent=$rendererContent.Replace($renderNeedle,"    invoke-static {}, Lmoe/practice/PracticeOverlay;->frame()V`n`n"+$renderNeedle)
 [IO.File]::WriteAllText($renderer,$rendererContent,[Text.UTF8Encoding]::new($false))
}
& "$java\java.exe" -jar $ApktoolJar b $decoded -o "$build\shell.apk"
CheckExit
& $Python -c 'from pathlib import Path; import sys,zipfile; Path(sys.argv[2]).write_bytes(zipfile.ZipFile(sys.argv[1]).read(sys.argv[3]))' "$build\shell.apk" "$build\classes2.dex" 'classes2.dex'
CheckExit
$password=$env:ARCPRACTICE_KEYSTORE_PASS
if(-not $password -and (Test-Path -LiteralPath $KeyStorePasswordFile)){$password=[IO.File]::ReadAllText($KeyStorePasswordFile).Trim()}
if(-not(Test-Path -LiteralPath $KeyStore)){
 if(-not $password){
  $password=[Guid]::NewGuid().ToString('N')
  New-Item -ItemType Directory -Force (Split-Path $KeyStorePasswordFile) | Out-Null
  [IO.File]::WriteAllText($KeyStorePasswordFile,$password,[Text.UTF8Encoding]::new($false))
 }
 New-Item -ItemType Directory -Force (Split-Path $KeyStore) | Out-Null
}
if(-not $password){throw 'Existing keystore needs ARCPRACTICE_KEYSTORE_PASS or -KeyStorePasswordFile'}
# Environment arguments keep the signing password out of process command lines.
$previousPassword=$env:ARCPRACTICE_SIGNING_PASS
$env:ARCPRACTICE_SIGNING_PASS=$password
try {
if(-not(Test-Path -LiteralPath $KeyStore)){
 & "$java\keytool.exe" -genkeypair -keystore $KeyStore -storepass:env ARCPRACTICE_SIGNING_PASS -keypass:env ARCPRACTICE_SIGNING_PASS -alias $KeyAlias -keyalg RSA -keysize 2048 -validity 10000 -dname 'CN=Arcaea Local Practice'
 CheckExit
}
$variant=if($TestOnly){'test'}else{'full'}
if($PackageName -ne 'moe.inf.arc'){$variant='standalone-'+$variant}
$un="$build\$variant-unsigned.apk"
if($TestOnly){& $Python "$PSScriptRoot\repack.py" $source $un --test --package-name $PackageName}else{& $Python "$PSScriptRoot\repack.py" $source $un --package-name $PackageName}
CheckExit
& "$bt\zipalign.exe" -P 16 -f 4 $un "$build\$variant-aligned.apk"
CheckExit
$output=Join-Path $OutputDir "Arcaea-Infinity-7.0.1f-Practice-$variant.apk"
& "$bt\apksigner.bat" sign --ks $KeyStore --ks-key-alias $KeyAlias --ks-pass env:ARCPRACTICE_SIGNING_PASS --key-pass env:ARCPRACTICE_SIGNING_PASS --out $output "$build\$variant-aligned.apk"
CheckExit
& "$bt\apksigner.bat" verify --verbose $output
CheckExit
& "$bt\zipalign.exe" -c -P 16 4 $output
CheckExit
Write-Output $output
} finally {$env:ARCPRACTICE_SIGNING_PASS=$previousPassword}
