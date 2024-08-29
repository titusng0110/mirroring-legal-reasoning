import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
import string

# Ensure the necessary NLTK resources are downloaded
nltk.download('punkt')
nltk.download('wordnet')
nltk.download('averaged_perceptron_tagger')

# Function to get part of speech tag for lemmatization
def get_wordnet_pos(word):
    """Map POS tag to first character lemmatize() accepts"""
    tag = nltk.pos_tag([word])[0][1][0].upper()
    tag_dict = {
        'J': wordnet.ADJ,
        'N': wordnet.NOUN,
        'V': wordnet.VERB,
        'R': wordnet.ADV
    }
    return tag_dict.get(tag, wordnet.NOUN)

def preprocess_text(text):
    # Initialize the lemmatizer and custom stop words list
    lemmatizer = WordNetLemmatizer()
    custom_stopwords = set([
        'ever', 'hardly', 'hence', 'into', 'nor', 'were', 'viz', 'all', 'also', 'am', 'an',
        'and', 'any', 'are', 'as', 'at', 'be', 'because', 'been', 'could', 'did', 'do', 'does',
        'e.g.', 'from', 'had', 'has', 'have', 'having', 'he', 'her', 'here', 'hereby', 'herein',
        'hereof', 'hereon', 'hereto', 'herewith', 'him', 'his', 'however', 'i.e.', 'if', 'is',
        'it', 'its', 'me', 'of', 'on', 'onto', 'or', 'our', 'really', 'said', 'she', 'should',
        'so', 'some', 'such', 'than', 'that', 'the', 'their', 'them', 'then', 'there', 'thereby',
        'therefore', 'therefrom', 'therein', 'thereof', 'thereon', 'thereto', 'therewith', 'these',
        'they', 'this', 'those', 'thus', 'to', 'too', 'unto', 'us', 'very', 'was', 'we', 'what',
        'when', 'where', 'whereby', 'wherein', 'whether', 'which', 'who', 'whom', 'whose', 'why',
        'with', 'would', 'you'
    ])
    
    # Tokenize the text
    tokens = word_tokenize(text)
    
    # Convert to lower case, remove punctuation and lemmatize
    processed_tokens = [
        token.lower()
        for token in tokens 
        if token.lower() not in custom_stopwords and token not in string.punctuation
    ]

    lemmatized_tokens = [lemmatizer.lemmatize(token, get_wordnet_pos(token)) for token in processed_tokens]
    
    return lemmatized_tokens
