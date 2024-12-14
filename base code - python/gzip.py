# Author: Marco Simoes
# Adapted from Java's implementation of Rui Pedro Paiva
# Teoria da Informacao, LEI, 2022

import sys
from huffmantree import HuffmanTree

def traverse(arr, node, current_code):
    if node.isLeaf():
        if node.index != -1:  # Verifica se é o ultimo
            arr[node.index] = current_code
        return

    if node.left:
        traverse(arr, node.left, current_code + '0')  
    if node.right:
        traverse(arr, node.right, current_code + '1')  

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
        idx = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]
        clen_len = [0 for i in range(19)]

        for i in range(0, hclen+4):
            temp = self.readBits(3)
            clen_len[idx[i]] = temp
        return clen_len

    def huffmanFromLens(self, lenArray):
        htr = HuffmanTree()
        max_len = max(lenArray)
        max_symbol = len(lenArray)
        
        bl_count = [0 for i in range(max_len+1)]
        for N in range(1, max_len+1):
            bl_count[N] += lenArray.count(N)

        code = 0
        next_code = [0 for i in range(max_len+1)]
        for bits in range(1, max_len+1):
            code = (code + bl_count[bits-1]) << 1
            next_code[bits] = code
  
        for n in range(max_symbol):
            length = lenArray[n]
            if(length != 0):
                code = bin(next_code[length])[2:]
                extension = "0"*(length-len(code)) 
                htr.addNode(extension + code, n, False)
                next_code[length] += 1
        
        return htr;

    def treeCodeLens(self, size, hufftree):
        # Array que irá armazenar os comprimentos dos códigos de Huffman
        ht_lens = [] 
        prev = 0  # Variável para armazenar o código anterior, usada em alguns casos específicos

        # Loop até que o array 'ht_lens' atinja o tamanho desejado
        while (len(ht_lens) < size):
            hufftree.resetCurNode()  # Reinicia o nó atual da árvore de Huffman

            # Variável para verificar se o próximo nó foi encontrado
            found = False
            
            # Procura pelo próximo nó
            while(not found):
                # Lê um bit e tenta seguir para o próximo nó da árvore de Huffman com base no bit lido
                bit = self.readBits(1)  
                codigo = hufftree.nextNode(str(bit))  # Obtém o código associado ao nó atual
                if(codigo != -1 and codigo != -2):  # Verifica se o código é válido (diferente de -1 e -2)
                    found = True  # Se encontrou um código válido, termina a procura

            # Caso o código seja 18 (indicado para 7 bits extra), lê mais 7 bits
            if(codigo == 18): 
                amount = self.readBits(7)  # Lê os 7 bits extras
                # Adiciona 0 ao array 'ht_lens' para o comprimento do código, ajustando com base nos bits lidos
                ht_lens += [0]*(11 + amount)

            # Caso o código seja 17 (indicado para 3 bits extra), lê mais 3 bits
            if(codigo == 17):
                amount = self.readBits(3)  # Lê os 3 bits extras
                # Adiciona 0 ao array 'ht_lens' para o comprimento do código, ajustando com base nos bits lidos
                ht_lens += [0]*(3 + amount)

            # Caso o código seja 16 (indicado para 2 bits extra), lê mais 2 bits
            if(codigo == 16):
                amount = self.readBits(2)  # Lê os 2 bits extras
                # Adiciona ao array 'ht_lens' o valor do código anterior ajustado com base nos bits lidos
                ht_lens += [prev]*(3 + amount)

            # Se o código for entre 0 e 15, é adicionado diretamente ao array de comprimentos
            elif(codigo >= 0 and codigo <= 15):
                ht_lens += [codigo]
                prev = codigo  # Atualiza o código anterior

        # Retorna o array contendo os comprimentos dos códigos de Huffman
        return ht_lens


    def decompress_LZ77(self, huffman_tree_litlen, huffman_tree_dist, out):
        """
        Função principal para descompressão LZ77.
        Lê os códigos de comprimento/literal e distância e descomprime os dados.
        """
        while True:
            code_litlen = self._read_huffman_code(huffman_tree_litlen)

            if code_litlen == 256:  # Código de fim de bloco
                break

            if code_litlen < 256:  # Literal
                out.append(code_litlen)
            else:  # Comprimento/Distância
                length = self._calculate_length(code_litlen)
                distance = self._calculate_distance(huffman_tree_dist)
                for _ in range(length):
                    out.append(out[-distance])

        return out

    def _read_huffman_code(self, huffman_tree):
        """
        Lê um código da árvore de Huffman fornecida bit a bit.
        """
        huffman_tree.resetCurNode()

        while True:
            bit = str(self.readBits(1))
            code = huffman_tree.nextNode(bit)
            if code != -1 and code != -2:  # Encontrou uma folha
                return code

    def _calculate_length(self, code_litlen):
        """
        Calcula o comprimento com base no código de comprimento/literal.
        """
        extra_litlen_bits = [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0]
        extra_litlen_lens = [11, 13, 15, 17, 19, 23, 27, 31, 35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227, 258]

        if code_litlen < 265:
            return code_litlen - 257 + 3

        index = code_litlen - 265
        extra_bits = self.readBits(extra_litlen_bits[index])
        return extra_litlen_lens[index] + extra_bits

    def _calculate_distance(self, huffman_tree_dist):
        """
        Calcula a distância com base na árvore de Huffman de distâncias.
        """
        extra_dist_bits = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13]
        extra_dist_lens = [5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385, 513, 769, 1025, 1537, 2049, 3073, 4097, 6145, 8193, 12289, 16385, 24577]

        code_dist = self._read_huffman_code(huffman_tree_dist)

        if code_dist < 4:
            return code_dist + 1

        index = code_dist - 4
        extra_bits = self.readBits(extra_dist_bits[index])
        return extra_dist_lens[index] + extra_bits

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
        f = open(self.gzh.fName, 'wb')
        out = []

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
            print("-----------  EX 1  -----------")
            hlit, hdist, hlen = self.ex1()
            print(f"HLIT: {hlit}, HDIST: {hdist}, HCLEN: {hlen}")

            # ex 2 --- Crie um método que armazene num array os comprimentos dos códigos 
            # do “alfabeto de comprimentos de códigos”, com base em HCLEN: 
            print("-----------  EX 2  -----------")
            clen_code_lens = self.ex2(hlen)
            print(clen_code_lens)

            # ex 3 --- Crie um método que converta os comprimentos dos códigos da alínea 
            # anterior em códigos de Huffman do "alfabeto de comprimentos de 
            # códigos"; 
            print("-----------  EX 3  -----------")
            huffman_tree_clens = self.huffmanFromLens(clen_code_lens)          

            byte_array = [''] *64
            traverse(byte_array, huffman_tree_clens.root, "")
            print(byte_array)

            # ex 4 --- Crie um método que leia e armazene num array os HLIT + 257 comprimentos dos códigos referentes ao alfabeto de literais/comprimentos,
            # codificados segundo o código de Huffman de comprimentos de códigos: 
            litlen_code_lens = self.treeCodeLens(hlit + 257, huffman_tree_clens)        
            print("-----------  EX 4  -----------")

            dict_hdist = {}
            for numero in litlen_code_lens:
                if numero in dict_hdist:
                    dict_hdist[numero] += 1
                else:
                    dict_hdist[numero] = 1

            print(dict_hdist)

            # ex 5 --- Crie um método que leia e armazene num array os HDIST + 1 
            # comprimentos de código referentes ao alfabeto de distâncias, 
            # codificados segundo o código de Huffman de comprimentos de códigos 

            print("-----------  EX 5  -----------")
            dist_code_lens = self.treeCodeLens(hdist + 1, huffman_tree_clens)
            print(dist_code_lens)

            # ex 6 --- Usando o método do ponto 3), determine os códigos de Huffman 
            # referentes aos dois alfabetos (literais / comprimentos e distâncias) e 
            # armazene-os num array (ver Doc5).

            huffman_tree_litlen = self.huffmanFromLens(litlen_code_lens)
            huffman_tree_dist = self.huffmanFromLens(dist_code_lens)

            # ex 7 --- Crie as funções necessárias à descompactação dos dados comprimidos, 
            # com base nos códigos de Huffman e no algoritmo LZ77
            out = self.decompress_LZ77(huffman_tree_litlen, huffman_tree_dist, out)

            # ex 8 --- Grave os dados descompactados num ficheiro com o nome original 
            # (consulte a estrutura gzipHeader, nomeadamente o campo fName e 
            # analize a função getHeader do ficheiro gzip.cpp). 

            if(len(out) > 32768):
                # Write every charater that exceeds the 327680 range to the file
                f.write(bytes(out[0 : len(out) - 32768]))
                # Keep the rest in the out array
                out = out[len(out) - 32768 :]

            # if(len(out) > 32768):
            #     string += str(out[0 : len(out) - 32768])
            #     out = out[len(out) - 32768 :]
            # else:
            #     print(out)
            #     string += ''.join(chr(num) for num in out)



            numBlocks += 1

        # Escrever os bytes restantes
        f.write(bytes(out))

        # Fechar o ficheiro descompactado
        f.close

        # Fechar o ficheiro lido 
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
            # byte = self.f.read(1)
            # if not byte:
            #     raise EOFError("Fim inesperado do ficheiro.")
            self.bits_buffer = self.f.read(1)[0] << self.available_bits | self.bits_buffer
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
