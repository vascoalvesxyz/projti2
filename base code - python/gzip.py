# Author: Marco Simoes
# Adapted from Java's implementation of Rui Pedro Paiva
# Teoria da Informacao, LEI, 2022

import sys
from huffmantree import HuffmanTree

class GZIPHeader:
    ''' class for reading and storing GZIP header fields '''

    ID1 = ID2 = CM = FLG = XFL = OS = 0
    MTIME = []
    lenMTIME = 4
    mTime = 0

    # bits 0, 1, 2, 3 and 4, respectively (remaining 3 bits: reserved)
    FLG_FTEXT = FLG_FHCRC = FLG_FEXTRA = FLG_FNAME = FLG_FCOMMENT = 0

    # FLG_FTEXT --> ignored (usually 0)
    # if FLG_FEXTRA == 1
    XLEN, extraField = [], []
    lenXLEN = 2

    # if FLG_FNAME == 1
    fName = ''  # ends when a byte with value 0 is read

    # if FLG_FCOMMENT == 1
    fComment = ''  # ends when a byte with value 0 is read

    # if FLG_HCRC == 1
    HCRC = []

    def read(self, f):
        ''' reads and processes the Huffman header from file. Returns 0 if no error, -1 otherwise '''

        # ID 1 and 2: fixed values
        self.ID1 = f.read(1)[0]
        if self.ID1 != 0x1f: return -1  # error in the header

        self.ID2 = f.read(1)[0]
        if self.ID2 != 0x8b: return -1  # error in the header

        # CM - Compression Method: must be the value 8 for deflate
        self.CM = f.read(1)[0]
        if self.CM != 0x08: return -1  # error in the header

        # Flags
        self.FLG = f.read(1)[0]

        # MTIME
        self.MTIME = [0] * self.lenMTIME
        self.mTime = 0
        for i in range(self.lenMTIME):
            self.MTIME[i] = f.read(1)[0]
            self.mTime += self.MTIME[i] << (8 * i)

        # XFL (not processed...)
        self.XFL = f.read(1)[0]

        # OS (not processed...)
        self.OS = f.read(1)[0]

        # --- Check Flags
        self.FLG_FTEXT = self.FLG & 0x01
        self.FLG_FHCRC = (self.FLG & 0x02) >> 1
        self.FLG_FEXTRA = (self.FLG & 0x04) >> 2
        self.FLG_FNAME = (self.FLG & 0x08) >> 3
        self.FLG_FCOMMENT = (self.FLG & 0x10) >> 4

        # FLG_EXTRA
        if self.FLG_FEXTRA == 1:
            # read 2 bytes XLEN + XLEN bytes de extra field
            # 1st byte: LSB, 2nd: MSB
            self.XLEN = [0] * self.lenXLEN
            self.XLEN[0] = f.read(1)[0]
            self.XLEN[1] = f.read(1)[0]
            #self.xlen = self.XLEN[1] << 8 + self.XLEN[0]
            self.xlen = (self.XLEN[1] << 8) + self.XLEN[0]

            # read extraField and ignore its values
            self.extraField = f.read(self.xlen)

        def read_str_until_0(f):
            s = ''
            while True:
                c = f.read(1)[0]
                if c == 0:
                    return s
                s += chr(c)

        # FLG_FNAME
        if self.FLG_FNAME == 1:
            self.fName = read_str_until_0(f)

        # FLG_FCOMMENT
        if self.FLG_FCOMMENT == 1:
            self.fComment = read_str_until_0(f)

        # FLG_FHCRC (not processed...)
        if self.FLG_FHCRC == 1:
            self.HCRC = f.read(2)

        return 0


class GZIP:
    ''' class for GZIP decompressing file (if compressed with deflate) '''

    gzh = None
    gzFile = ''
    fileSize = origFileSize = -1
    numBlocks = 0
    f = None

    bits_buffer = 0
    available_bits = 0

    def __init__(self, filename):
        self.gzFile = filename
        self.f = open(filename, 'rb')
        self.f.seek(0, 2)
        self.fileSize = self.f.tell()
        self.f.seek(0)


    ### Exercício 1 a 8 ###
    def ex1(self):
        HLIT = self.readBits(5)
        HDIST = self.readBits(5)
        HCLEN = self.readBits(4)
        return HLIT, HDIST, HCLEN

    def ex2(self, hclen):
        ordem = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]
        comprimentos = [0] * 19  # Inicializar a zero

        for i in range(hclen):
            comprimentos[ordem[i]] = self.readBits(3)

        return comprimentos 

    def huffmanFromLens(self, hclen_array):
        htr = HuffmanTree() 

        max_len = max(hclen_array) # max_len is the code with the largest length 
        max_symbol = len(hclen_array) # max_symbol é o maior símbolo a codificar

        bl_count = [0 for i in range(max_len+1)]
        # Get array with number of codes with length N (bl_count)
        for N in range(1, max_len+1):
            bl_count[N] += hclen_array.count(N)

        # Get first code of each code length 
        code = 0
        next_code = [0 for i in range(max_len+1)]
        for bits in range(1, max_len+1):
            code = (code + bl_count[bits-1]) << 1
            next_code[bits] = code

        # Define codes for each symbol in lexicographical order
        for n in range(max_symbol):
            # Length associated with symbol n 
            length = hclen_array[n]
            if(length != 0):
                code = bin(next_code[length])[2:]
                # In case there are 0s at the start of the code, we have to add them manualy
                # length-len(code) 0s have to be added
                extension = "0"*(length-len(code)) 
                htr.addNode(extension + code, n, False)
                next_code[length] += 1

        return htr

    def treeCodeLens(self, size, hufftree):

        # Array dos comprimentos
        ht_lens = [] 
        prev = 0

        while (len(ht_lens) < size):
            hufftree.resetCurNode()

            # Procurar próximo nó
            found = False
            while(not found):
                bit = self.readBits(1)
                codigo = hufftree.nextNode(str(bit))
                if(codigo != -1 and codigo != -2):
                    found = True
            
            if(codigo == 18): # 18 - 7 extra bits 
                amount = self.readBits(7)
                ht_lens += [0]*(11 + amount)
            if(codigo == 17):
                amount = self.readBits(3) # 17 - 3 extra bits
                ht_lens += [0]*(3 + amount)
            if(codigo == 16): # 16 - 2 extra bits
                amount = self.readBits(2)
                ht_lens += [prev]*(3 + amount)
            elif(codigo >= 0 and codigo <= 15):
                ht_lens += [codigo]
                prev = codigo

        return ht_lens


    def decompress_LZ77(self, huffman_tree_litlen, huffman_tree_dist, out):
        # Definição dos arrays que indicam a quantidade extra de bits necessários para os códigos LITLEN e DIST.
        extra_litlen_bits = [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0]
        extra_litlen_lens = [11, 13, 15, 17, 19, 23, 27, 31, 35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227, 258]

        extra_dist_bits = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13]
        extra_dist_lens = [5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385, 513, 769, 1025, 1537, 2049, 3073, 4097, 6145, 8193, 12289, 16385, 24577]

        # Inicializa o código LITLEN com um valor inválido
        code_litlen = -1

        # Enquanto o código LITLEN não for 256, continua a descomprimir
        while(code_litlen != 256):
            huffman_tree_litlen.resetCurNode()  # Reseta o nó atual da árvore Huffman para LITLEN

            found_litlen = False
            dist_found = True

            # Laço para encontrar o código LITLEN
            while(not found_litlen):
                try:
                    cur_bit = str(self.readBits(1))  # Lê o próximo bit
                except EOFError as e:
                    print("Fim inesperado do stream de entrada.")
                    return out

                # Avança na árvore Huffman com o bit lido
                code_litlen = huffman_tree_litlen.nextNode(cur_bit)

                # Se o código encontrado for válido e não for -1 ou -2 (códigos inválidos)
                if (code_litlen != -1 and code_litlen != -2):
                    found_litlen = True

                    # Se o código LITLEN for menor que 256, é um literal
                    if(code_litlen < 256):
                        out += [code_litlen]  # Adiciona o valor literal à saída

                    # Se o código LITLEN for maior que 256, é uma referência de distância (código de back-reference)
                    if(code_litlen > 256):
                        dist_found = False

                        # Calcula o comprimento do back-reference
                        if(code_litlen < 265):
                            length = code_litlen - 257 + 3
                        else:
                            dif = code_litlen - 265
                            read_extra = extra_litlen_bits[dif]
                            len_extra = extra_litlen_lens[dif]
                            length = len_extra + self.readBits(read_extra)

                        # Reseta o nó atual da árvore Huffman para DIST
                        huffman_tree_dist.resetCurNode()

                        # Laço para encontrar a distância do back-reference
                        while(not dist_found):
                            dist_bit = str(self.readBits(1))  # Lê o próximo bit para distância
                            code_dist = huffman_tree_dist.nextNode(dist_bit)

                            # Se o código DIST for válido e não for -1 ou -2
                            if(code_dist != -1 and code_dist != -2):
                                dist_found = True
                                # Se o código DIST for menor que 4, a distância é o código DIST + 1
                                if(code_dist < 4):
                                    distance = code_dist + 1
                                else:
                                    dif = code_dist - 4
                                    read_extra = extra_dist_bits[dif]
                                    dist_extra = extra_dist_lens[dif]
                                    distance = dist_extra + self.readBits(read_extra)

                                # Adiciona os valores referenciados de volta à saída, conforme o comprimento
                                for i in range(length):
                                    out.append(out[-distance])

        return out  # Retorna os dados descomprimidos

    def decompress(self):
        ''' main function for decompressing the gzip file with deflate algorithm '''

        numBlocks = 0

        # get original file size: size of file before compression
        origFileSize = self.getOrigFileSize()
        print(origFileSize)

        # read GZIP header
        error = self.getHeader()
        if error != 0:
            print('Formato invalido!')
            return

        # show filename read from GZIP header
        print(self.gzh.fName)

        # MAIN LOOP - decode block by block
        f = open(self.gzh.fName, 'w')
        out = []
        string = ""

        BFINAL = 0
        while not BFINAL == 1:

            BFINAL = self.readBits(1)
            BTYPE = self.readBits(2)
            if BTYPE != 2:
                print('Error: Block %d not coded with Huffman Dynamic coding' % (numBlocks + 1))
                return

            # --- STUDENTS --- ADD CODE HERE

            # ex 1 --- Crie um método que leia o formato do bloco (i.e., devolva o valor 
            # correspondente a HLIT, HDIST e HCLEN), de acordo com a estrutura de 
            hlit, hdist, hlen = self.ex1()
            print(f"HLIT: {hlit}, HDIST: {hdist}, HCLEN: {hlen}")

            # ex 2 --- Crie um método que armazene num array os comprimentos dos códigos 
            # do “alfabeto de comprimentos de códigos”, com base em HCLEN: 
            clen_comprimentos = self.ex2(hlen)
            print(clen_comprimentos)

            # ex 3 --- Crie um método que converta os comprimentos dos códigos da alínea 
            # anterior em códigos de Huffman do "alfabeto de comprimentos de 
            # códigos"; 
            huffman_clen = self.huffmanFromLens(clen_comprimentos)          
            print(huffman_clen)

            # ex 4 --- Crie um método que leia e armazene num array os HLIT + 257 
            # comprimentos dos códigos referentes ao alfabeto de literais/comprimentos,
            # codificados segundo o código de Huffman de comprimentos de códigos: 
            arr_clen_literais = self.treeCodeLens(hlit + 257, huffman_clen)        
            print(arr_clen_literais)

            # ex 5 --- Crie um método que leia e armazene num array os HDIST + 1 
            # comprimentos de código referentes ao alfabeto de distâncias, 
            # codificados segundo o código de Huffman de comprimentos de códigos 
            huffman_clen_literais = self.huffmanFromLens(arr_clen_literais)

            # ex 6 --- Usando o método do ponto 3), determine os códigos de Huffman 
            # referentes aos dois alfabetos (literais / comprimentos e distâncias) e 
            # armazene-os num array (ver Doc5).
            arr_hdist_comprimentos = self.treeCodeLens(hdist + 1, huffman_clen_literais)
            print(arr_hdist_comprimentos) 

            # ex 7 --- Crie as funções necessárias à descompactação dos dados comprimidos, 
            # com base nos códigos de Huffman e no algoritmo LZ77
            huf_hdist_comprimentos = self.huffmanFromLens(arr_hdist_comprimentos)

            out += self.decompress_LZ77(huffman_clen_literais, huf_hdist_comprimentos, out)

            # ex 8 --- Grave os dados descompactados num ficheiro com o nome original 
            # (consulte a estrutura gzipHeader, nomeadamente o campo fName e 
            # analize a função getHeader do ficheiro gzip.cpp). 
            if(len(out) > 32768):
                string += str(out[0 : len(out) - 32768])
                out = out[len(out) - 32768 :]
            else:
                print(out)
                string += ''.join(chr(num) for num in out)



            numBlocks += 1

        print(string)
        f.write(string)
        # f.write(str((out)))
        f.close()
        # close file
        self.f.close()
        print("End: %d block(s) analyzed." % numBlocks)

    def getOrigFileSize(self):
        ''' reads file size of original file (before compression) - ISIZE '''

        # saves current position of file pointer
        fp = self.f.tell()

        # jumps to end-4 position
        self.f.seek(self.fileSize - 4)

        # reads the last 4 bytes (LITTLE ENDIAN)
        sz = 0
        for i in range(4):
            byte = self.f.read(1)[0]
            sz += byte << (8 * i)

        # restores file pointer to its original position
        self.f.seek(fp)

        return sz

    def getHeader(self):
        ''' reads GZIP header'''

        self.gzh = GZIPHeader()
        header_error = self.gzh.read(self.f)
        return header_error

    def readBits(self, n, keep=False):
        while self.available_bits < n:
            byte = self.f.read(1)
            if not byte:
                raise EOFError("Fim inesperado do ficheiro.")
            self.bits_buffer = (byte[0] << self.available_bits) | self.bits_buffer
            self.available_bits += 8

        mask = (2 ** n) - 1
        value = self.bits_buffer & mask

        if not keep:
            self.bits_buffer >>= n
            self.available_bits -= n

        return value


if __name__ == '__main__':

    # gets filename from command line if provided
    fileName = "FAQ.txt.gz"
    if len(sys.argv) > 1:
        fileName = sys.argv[1]

    # decompress file
    gz = GZIP(fileName)
    gz.decompress()
