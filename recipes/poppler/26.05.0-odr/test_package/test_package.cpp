#include <poppler-document.h>

#include <iostream>

using namespace poppler;

std::string minimal_pdf = R"(%PDF-1.0
1 0 obj
<</Type/Catalog/Pages 2 0 R>>
endobj
2 0 obj
<</Kids[3 0 R]/Count 1/Type/Pages/MediaBox[0 0 595 792]>>
endobj
3 0 obj
<</Type/Page/Parent 2 0 R/Contents 4 0 R/Resources<<>>>>
endobj
xref
0 0
trailer
<</Size 5/Root 1 0 R>>
startxref
316
%%EOF)";

int main() {
    auto doc = document::load_from_data(minimal_pdf.data());
    std::cout << "#pages: " << doc->pages() << '\n';
    return 0;
}
