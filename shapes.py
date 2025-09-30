import numpy as np


class Shape():
    def __init__(self, sides, length, regular):
        self.sides = sides
        self.regular = regular
        self.length = length

        if not regular:
            exit("This program only deals with regular shapes, Exiting...")
    
    def area(self):
        #A = (n * s²) / (4 * tan(180°/n)) 
        return (self.sides * (self.length**2)) / (4 * np.tan(np.radians(180/self.sides)))
    
    def perimeter(self):
        return self.sides * self.length


if __name__ == "__main__":
    
    sides = int(input("Enter number of sides: "))
    length = float(input("Enter length of each side: "))
    regular = input("Is the shape regular? (y/n): ").lower() == 'y'

    shape = Shape(sides, length, regular)

    print(f"Area: {shape.area()}")
    print(f"Perimeter: {shape.perimeter()}")
