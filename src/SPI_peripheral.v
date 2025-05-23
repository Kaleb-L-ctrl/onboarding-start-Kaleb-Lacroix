/*
 * Copyright (c) 2025 Kaleb Lacroix
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module SPI_peripheral (
    input wire SCLK,
    input wire nCS,
    input wire COPI,
    input wire clk,
    input wire rst_n,

    output reg [7:0] en_reg_out_7_0,
    output reg [7:0] en_reg_out_15_8,
    output reg [7:0] en_reg_pwm_7_0,
    output reg [7:0] en_reg_pwm_15_8,
    output reg [7:0] pwm_duty_cycle
);

    reg [1:0] SCLK_sync;
    reg [1:0] ncs_sync;
    reg [1:0] copi_sync;
   
    
    reg [4:0] counter;
    reg [15:0] copi_message;

    wire SCLKRISE       = (SCLK_sync == 2'b01);
    wire NCSLOW         = (ncs_sync == 2'b00);
    wire NCS_falling    = (ncs_sync == 2'b10);

    always @(posedge clk or negedge rst_n) begin//      on internal clock we sample through our buffers
        if (!rst_n)begin //                             reset (active low)
            SCLK_sync       <= 2'b00;
            copi_sync       <= 2'b00;
            ncs_sync        <= 2'b00;
          
            en_reg_out_7_0  <= 8'b0;
            en_reg_out_15_8 <= 8'b0;
            en_reg_pwm_7_0  <= 8'b0;
            en_reg_pwm_15_8 <= 8'b0;
            pwm_duty_cycle  <= 8'b0;

            counter         <= 5'b0;
            copi_message    <= 16'b0;


        end else begin//                                not reset; we capture values from contrtoler
            SCLK_sync <= {SCLK_sync[0], SCLK};//        zomg synchronizer for inputs to avoid metastability in logic operations
            copi_sync <= {copi_sync[0], COPI};
            ncs_sync  <= {ncs_sync[0], nCS};

        
            if (NCS_falling)begin//                     falling edge we are about to recieve a message get ready (reset old message-related registers)
                counter <= 5'b0;
                copi_message <= 16'b0;
            end
            
            else if(SCLKRISE && NCSLOW) begin//         incoming data is valid take samples
                if (counter != 16)begin//               stop sampling after getting the 16 bits
                    copi_message <= {copi_message[14:0], copi_sync[1]};//load in the new bitl, shuffle over others
                    counter <= counter + 1;
                end
            end
        
            if (counter==16) begin
                if (copi_message[15])begin//            we ignore read
                    case (copi_message[14:8])
                        7'h00:en_reg_out_7_0  <= copi_message[7:0];
                        7'h01:en_reg_out_15_8 <= copi_message[7:0];
                        7'h02:en_reg_pwm_7_0  <= copi_message[7:0];
                        7'h03:en_reg_pwm_15_8 <= copi_message[7:0];
                        7'h04:pwm_duty_cycle  <= copi_message[7:0];
                        default: ;//                    do nothing; we are ignoring invalid adresses
                    endcase
                end
            end
        end
    end

   


    
  // All output pins must be assigned. If not used, assign to 0.

  // List all unused inputs to prevent warnings
  //wire _unused = &{ena, clk, rst_n, 1'b0};

endmodule