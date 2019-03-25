"""Installation setup file
"""    
from setuptools import setup, find_packages

def description():
    """Description of package
    """
    with open('readme.rst') as f:
         return f.read()

setup(name='pipelineutils',
      packages=find_packages(),
      version='1.0.0',
      include_package_data=True,
      description='drone-pipeline workflow utilities',
      long_description=description(),
      author='Chris Schnaufer',
      author_email='schnaufer@email.arizona.edu',

      url='https://terraref.org',
      project_urls = {
        'Source': 'https://github.com/terraref/drone-pipeline',
        'Tracker': 'https://github.com/terraref/drone-pipeline/issues',
      },

      install_requires=[
          'pyclowder>=2,<3',
          'terrautils>=1'
      ],
      zip_safe=False,

      license='BSD',
      classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Database',
        'Topic :: Scientific/Engineering :: GIS',
        'Topic :: Utilities',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
      ],
      keywords=['terraref', 'clowder', 'field crop', 'phenomics', 'computer vision', 'remote sensing', 'drone', 'pipeline']
)
