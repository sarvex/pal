# coding: utf-8

import os
import scxutil


class HPUXPackageFile:
    def __init__(self, intermediateDir, targetDir, stagingDir, variables, sections):
        self.intermediateDir = intermediateDir
        self.targetDir = targetDir
        self.stagingDir = stagingDir
        self.variables = variables
        self.sections = sections
        self.tempDir = os.path.join(self.intermediateDir, "pkg-tmp")
        scxutil.MkAllDirs(self.tempDir)
        self.specificationFileName = os.path.join(self.tempDir, 'product_specification')
        self.configurePath = os.path.join(self.tempDir, "configure.sh")
        self.unconfigurePath = os.path.join(self.tempDir, "unconfigure.sh")
        self.preinstallPath = os.path.join(self.tempDir, "preinstall.sh")
        self.postremovePath = os.path.join(self.tempDir, "postremove.sh")
        self.fullversion_dashed = self.fullversion = self.variables["VERSION"]
        if "RELEASE" in self.variables:
            self.fullversion = self.variables["VERSION"] + "." + self.variables["RELEASE"]
            self.fullversion_dashed = self.variables["VERSION"] + "-" + self.variables["RELEASE"]

    def GeneratePackageDescriptionFiles(self):
        self.GenerateSpecificationFile()
        self.GenerateScripts()

    def GetScriptAsString(self, section):
        script = ""
        for line in self.sections[section]:
            script += line
            script += "\n"
        return script
        
    def GenerateScripts(self):
        with open(self.preinstallPath, 'w') as scriptfile:
            prein = self.variables["SHELL_HEADER"] + "\n"
            prein += """
BackupConfigurationFile() {
    mv "$1" "$1.swsave" > /dev/null 2>&1
}
"""
            prein += self.GetScriptAsString("Preinstall")

                # Make backups of conffiles
            for f in self.sections["Files"]:
                if f.type == "conffile":
                    prein += f"BackupConfigurationFile {f.stagedLocation}" + "\n"
            prein += "exit 0\n"
            scriptfile.write(prein)
        with open(self.configurePath, 'w') as scriptfile:
            configure = self.variables["SHELL_HEADER"] + "\n"
            configure += """
RestoreConfigurationFile() {
    mv "$1.swsave" "$1"
}
"""
                # Restore backups of conffiles
            for f in self.sections["Files"]:
                if f.type == "conffile":
                    configure += f"RestoreConfigurationFile {f.stagedLocation}" + "\n"

            configure += self.GetScriptAsString("Postinstall")
            configure += "exit 0\n"
            scriptfile.write(configure)
        with open(self.unconfigurePath, 'w') as scriptfile:
            unconf = self.GetScriptAsString("Preuninstall")
            unconf += "exit 0\n"
            scriptfile.write(unconf)
        with open(self.postremovePath, 'w') as scriptfile:
            postremove = self.GetScriptAsString("Postuninstall")
            postremove += "exit 0\n"
            scriptfile.write(postremove)
        
    def GenerateSpecificationFile(self):
        specfile = open(self.specificationFileName, 'w')

        specfile.write('depot\n')
        specfile.write('  layout_version   1.0\n')
        specfile.write('\n')
        specfile.write('# Vendor definition:\n')
        specfile.write('vendor\n')
        specfile.write('  tag           ' + self.variables["SHORT_NAME_PREFIX"] + '\n')
        specfile.write('  title         ' + self.variables["VENDOR"] + '\n')
        specfile.write('category\n')
        specfile.write('  tag           ' + self.variables["SHORT_NAME"] + '\n')
        specfile.write(f'  revision      {self.fullversion_dashed}' + '\n')
        specfile.write('end\n')
        specfile.write('\n')
        specfile.write('# Product definition:\n')
        specfile.write('product\n')
        specfile.write('  tag            ' + self.variables["SHORT_NAME"] + '\n')
        specfile.write(f'  revision       {self.fullversion_dashed}' + '\n')
        specfile.write('  architecture   HP-UX_B.11.00_32/64\n')
        specfile.write('  vendor_tag     ' + self.variables["SHORT_NAME_PREFIX"] + '\n')
        specfile.write('\n')
        specfile.write('  title          ' + self.variables["SHORT_NAME"] + '\n')
        if "RELEASE" in self.variables:
            specfile.write('  number         ' + self.variables["RELEASE"] + '\n')
        specfile.write('  category_tag   ' + self.variables["SHORT_NAME"] + '\n')
        specfile.write('\n')
        specfile.write('  description    ' + self.variables["DESCRIPTION"] + '\n')
        specfile.write('  copyright      ' + self.variables["HPUX_COPYRIGHT"] + '\n')
        if self.variables["PFARCH"] == 'ia64':
            specfile.write('  machine_type   ia64*\n')
        else:
            specfile.write('  machine_type   9000*\n')
        specfile.write('  os_name        HP-UX\n')
        specfile.write('  os_release     ?.11.*\n')
        specfile.write('  os_version     ?\n')
        specfile.write('\n')
        specfile.write('  directory      /\n')
        specfile.write('  is_locatable   false\n')
        specfile.write('\n')
        specfile.write('  # Fileset definitions:\n')
        specfile.write('  fileset\n')
        specfile.write('    tag          core\n')
        specfile.write('    title        ' + self.variables["SHORT_NAME"] + ' Core\n')
        specfile.write(f'    revision     {self.fullversion_dashed}' + '\n')
        specfile.write('\n')
        specfile.write('    # Dependencies\n')
        for dep in self.sections["Dependencies"]:
            specfile.write('    prerequisites ')
            specfile.write(dep)
            specfile.write('\n')
        specfile.write('    # Control files:\n')
        specfile.write(f'    configure     {self.configurePath}' + '\n')
        specfile.write(f'    unconfigure   {self.unconfigurePath}' + '\n')
        specfile.write(f'    preinstall    {self.preinstallPath}' + '\n')
        specfile.write(f'    postremove    {self.postremovePath}' + '\n')
        specfile.write('\n')
        specfile.write('    # Files:\n')

        # Now list all files in staging directory
        for f in self.sections["Files"] + self.sections["Directories"] + self.sections["Links"]:
            if f.type != "sysdir":
                specfile.write(
                    (
                        f'    file -m {str(f.permissions)} -o {f.owner} -g {f.group} {self.stagingDir}{f.stagedLocation} {f.stagedLocation}'
                        + '\n'
                    )
                )

        specfile.write('\n')
        specfile.write('  end # core\n')
        specfile.write('\n')
        specfile.write('end  # SD\n')

    def BuildPackage(self):
        if self.variables["PFARCH"] == 'pa-risc':
            arch = 'parisc'
        else:
            arch = self.variables["PFARCH"]

        if 'OUTPUTFILE' in self.variables:
            depotbasefilename = self.variables['OUTPUTFILE'] + '.depot'
        else:
            osversion = '11iv2' if int(self.variables["PFMINOR"]) < 30 else '11iv3'
            depotbasefilename = self.variables["SHORT_NAME"] + '-' + \
                    self.fullversion_dashed + \
                    '.hpux.' + osversion + '.' + arch + '.depot'
        depotfilename = os.path.join(self.targetDir, depotbasefilename)

        if "SKIP_BUILDING_PACKAGE" in self.variables:
            return

        retval = os.system('/usr/sbin/swpackage -s ' + 
                           os.path.join(self.tempDir, self.specificationFileName) + 
                           ' -x run_as_superuser=false -x admin_directory=' + 
                           self.intermediateDir + 
                           ' -x media_type=tape @ ' + 
                           depotfilename)
        if retval != 0:
            print("Error: swpackage returned non-zero status.")
            exit(1)

        with open(f"{self.targetDir}/package_filename", 'w') as package_filename:
            package_filename.write("%s\n" % depotbasefilename)
