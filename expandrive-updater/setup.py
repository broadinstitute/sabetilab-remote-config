from distutils.core import setup
import py2exe

#setup(console=['get-all-dns-nodes.py'])

setup(
        options = {
            'py2exe': {
                'optimize': 0,
                'bundle_files': 1,
                'compressed': True,
                'packages': ['boto.cacerts', 'boto'],
                }
            },
        console=['update-expandrive-from-dns.py'],
        data_files=[(r'boto\cacerts', [r'C:\Python34\Lib\site-packages\boto\cacerts\cacerts.txt']),
                    (r'boto', [r'C:\Python34\Lib\site-packages\boto\endpoints.json'])],
        package_data = {
           "boto.cacerts": ["cacerts.txt"],
           "boto": ["endpoints.json"],
        },
        zipfile=None
    )