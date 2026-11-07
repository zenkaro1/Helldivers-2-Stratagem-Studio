Add-Type -AssemblyName System.Drawing

$src = 'C:\Projekte\Website Design\hd2-stratagem-studio\.tmp\shots\voice.png'
$img = [System.Drawing.Image]::FromFile($src)
$rect = New-Object System.Drawing.Rectangle(860, 555, 560, 100)
$crop = New-Object System.Drawing.Bitmap($rect.Width, $rect.Height)
$g = [System.Drawing.Graphics]::FromImage($crop)
$g.DrawImage($img, 0, 0, $rect, [System.Drawing.GraphicsUnit]::Pixel)
$g.Dispose()
$crop.Save('C:\Projekte\Website Design\hd2-stratagem-studio\.tmp\shots\history-crop.png', [System.Drawing.Imaging.ImageFormat]::Png)
$crop.Dispose()
$img.Dispose()
Write-Output "cropped"
