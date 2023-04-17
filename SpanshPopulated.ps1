## in Admin powershell do .. set-executionpolicy remotesigned 

$folder = $Env:APPDATA+"\BGS"
$gzfile   = $folder+"\galaxy_populated.json.gz"
$spanshpopulated = "https://downloads.spansh.co.uk/galaxy_populated.json.gz"

Function DeGzip{
    Param(
        $infile,
        $outfile = ($infile -replace '\.gz$','')
        )

    $istream = New-Object System.IO.FileStream $inFile, ([IO.FileMode]::Open), ([IO.FileAccess]::Read), ([IO.FileShare]::Read)
    $ostream = New-Object System.IO.FileStream $outFile, ([IO.FileMode]::Create), ([IO.FileAccess]::Write), ([IO.FileShare]::None)
    $gzipStream = New-Object System.IO.Compression.GzipStream $istream, ([IO.Compression.CompressionMode]::Decompress)

    $buffer = New-Object byte[](1024)
    while($true){
        $read = $gzipstream.Read($buffer, 0, 1024)
        if ($read -le 0){break}
        $ostream.Write($buffer, 0, $read)
        }

    $gzipStream.Close()
    $ostream.Close()
    $istream.Close()
}

if(!(Test-Path -Path $folder))
{
    New-Item -ItemType Directory -Path $folder
}

Write-Host "Downloading to "$gzfile -f Yellow
$client = new-object System.Net.WebClient
$client.DownloadFile($spanshpopulated,$gzfile)
Write-Host "Download Done" -f Green

Write-Host "Decompress "$gzfile -f Yellow
DeGzip $gzfile
Write-Host "Decompress Done" -f Green


