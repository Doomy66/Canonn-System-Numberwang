from providers.EDSM import GetUnpopulated

s = GetUnpopulated()
for x in s:
    if x.name == 'Khun':
        print(x)
