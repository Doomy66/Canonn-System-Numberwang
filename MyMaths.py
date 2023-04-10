def sysdist(s1, s2):
    '''
    Actual Distance between 2 systems
    '''
    return((s1['x']-s2['x'])**2 + (s1['y']-s2['y'])**2 + (s1['z']-s2['z'])**2) ** 0.5

def cubedist(s1, s2):
    '''
    Cube Distance between 2 systems - The maximum delta
    '''
    return(max(abs(s1['x']-s2['x']) , abs(s1['y']-s2['y']) , abs(s1['z']-s2['z'])))
