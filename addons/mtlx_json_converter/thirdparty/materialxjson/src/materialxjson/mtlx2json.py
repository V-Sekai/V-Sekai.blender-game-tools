#!/usr/bin/env python
'''
Command to convert from  XML and JSON representation of a MaterialX document
'''
import MaterialX as mx
import core
import json
import os, argparse

def main():
    '''
    Command to convert from  XML and JSON representation of a MaterialX document
    '''
    parser = argparse.ArgumentParser(description="Utility to convert from XML to JSON representations of a MaterialX document")
    parser.add_argument('--outputPath', dest='outputPath', default='', help='File path to output results to.')
    parser.add_argument('--indent', dest='indent', type=int, default=2, help='Indentation for nested elements. Default is 2.')
    parser.add_argument('--compact', dest='compact', type=mx.stringToBoolean, default=False, help='Write in compact format. Default is False.')
    parser.add_argument('--skipLibraryElements', dest='skipLibraryElements', type=mx.stringToBoolean, default=True, help='Skip any library elements. Default is True.')
    parser.add_argument('--skipMaterials', dest='skipMaterials', type=mx.stringToBoolean, default=False, help='Skip any material elements. Default is False.')
    parser.add_argument('--skipAssignments', dest='skipAssignments', type=mx.stringToBoolean, default=False, help='Skip any material assignment elements. Default is False.')
    parser.add_argument(dest="inputFileName", help="Filename of the input document or folder containing input documents")

    opts = parser.parse_args()

    # Get absolute path of opts.outputPath
    if opts.outputPath:    
        opts.outputPath = os.path.abspath(opts.outputPath)
    outputPath = mx.FilePath(opts.outputPath)
    if outputPath.size() > 0:
        if os.path.isdir(outputPath.asString()):
            print('Output path "%s" does not exist.' % outputPath.asString())
            exit(-1)
        else:
            print('- Write files to outputPath: '+ opts.outputPath)

    # Get list of MaterialX files 
    fileList = []
    extension = 'mtlx'
    if os.path.isdir(opts.inputFileName): 
        extension = 'mtlx'   
        fileList = core.Util.getFiles(opts.inputFileName, extension)
    else:
        extension = mx.FilePath(opts.inputFileName).getExtension()
        if extension == 'mtlx':
            fileList.append(opts.inputFileName)

    if not fileList:
        print('No files found with extension "%s"' % extension)
        exit(-1)

    ## Create I/O handler
    mtlxjson = core.MaterialXJson()
    
    class Predicates:
        '''
        @brief Utility class to define predicates for skipping elements when iterating over elements in a document.
        '''
        def __init__(self):
            self.predicates = []

        def skip(self, elem: mx.Element):
            '''            
            @brief Utility to skip elements when iterating over elements in a document.
            '''
            for predicate in self.predicates:
                if not predicate(elem):
                    return False
            return True

    def skipLibraryElement(elem: mx.Element) -> bool:
        '''
        @brief Utility to skip library elements when iterating over elements in a document.
        @return True if the element is not in a library, otherwise False.
        '''
        return not elem.hasSourceUri()
    
    def skipAssignments(elem: mx.Element) -> bool:
        '''
        @brief Utility to skip material assignment elements when iterating over elements in a document.
        @return True if the element is not a material assignment, otherwise False.
        '''
        return elem.getCategory() not in ['materialassign', 'look', 'lookgroup']

    def skipMaterials(elem: mx.Element) -> bool:
        '''
        @brief Utility to skip material elements when iterating over elements in a document.
        @return True if the element is not a material element, otherwise False.
        '''
        if elem.getCategory() in ['surfacematerial'] or elem.getType() in ['surfaceshader', 'displacementshader', 'volumeshader']:
            return False
        return True

    for fileName in fileList:
        if mx.FilePath(fileName).isAbsolute():
            outputFilePath = mx.FilePath(fileName.replace('.mtlx', '_mtlx.json'))
        else:            
            outputFilePath = outputPath / mx.FilePath(fileName.replace('.mtlx', '_mtlx.json'))
        outputFileName = outputFilePath.asString()
        writeOptions = core.JsonWriteOptions()
        predicate = Predicates()        
        if opts.skipAssignments:
            predicate.predicates.append(skipAssignments)
        if opts.skipMaterials:
            predicate.predicates.append(skipMaterials)    
        if opts.skipLibraryElements:
            predicate.predicates.append(skipLibraryElement)
        writeOptions.elementPredicate = predicate.skip
        writeOptions.indent = opts.indent
        if opts.compact:
            writeOptions.separators = (',', ':')
            writeOptions.indent = None
        core.Util.xmlFileToJsonFile(fileName, outputFileName, writeOptions)
        print('Convert XML "%s" -> JSON  "%s"' % (fileName, outputFileName))
    
if __name__ == '__main__':
    main()
